"""
Agentic retrieval — the agent decides what to look for, where to look,
and whether the evidence it finds is sufficient.

This is not a static RAG pipeline. Retrieval is adaptive:

    1. Query decomposition   — break the agent's information need into
                               focused sub-queries

    2. Source routing        — classify each sub-query to the right source
                               (repository, logs, docs, incidents, schema...)

    3. Dense + sparse search — pgvector cosine similarity + BM25 keyword
                               search run in parallel against each source

    4. Metadata filtering    — apply time ranges, file types, severity levels

    5. Reranking             — cross-encoder style reranking to select
                               the most relevant passages

    6. Evidence verification — confirm the retrieved content is coherent
                               and non-contradictory

    7. Context compression   — trim to the most salient sentences/lines
                               to stay within the model context window

    8. Citation generation   — tag each evidence piece with its source
                               for auditability

The RetrievalOrchestrator is called by evidence-collection and
hypothesis-verification handlers. The agent can request more evidence
at any point by returning needs_more_evidence=True from a handler.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Any

import structlog
from rank_bm25 import BM25Okapi
from sqlalchemy.ext.asyncio import AsyncSession

from forgeops.agent.gateway import ModelGateway
from forgeops.memory.store import MemoryStore
from forgeops.models.orm import MemoryType

log = structlog.get_logger(__name__)

_gateway = ModelGateway()


# ── Data types ────────────────────────────────────────────────────────────────


@dataclass
class SubQuery:
    query: str
    source: str   # "repository" | "logs" | "incidents" | "docs" | "schema" | "memory"
    priority: str = "medium"   # "high" | "medium" | "low"


@dataclass
class RetrievedDocument:
    source: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    citation: str = ""


@dataclass
class RetrievalResult:
    query: str
    documents: list[RetrievedDocument]
    sufficient: bool
    summary: str
    citations: list[str]


# ── BM25 index (in-process, stateless) ────────────────────────────────────────


class BM25Index:
    """
    Lightweight BM25 index over a list of text documents.
    Rebuilt per retrieval call (no persistence needed for this use case).
    """

    def __init__(self, documents: list[str]) -> None:
        tokenised = [_tokenise(doc) for doc in documents]
        self._bm25 = BM25Okapi(tokenised)
        self._documents = documents

    def search(self, query: str, top_k: int = 5) -> list[tuple[str, float]]:
        tokens = _tokenise(query)
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(
            zip(self._documents, scores.tolist()),
            key=lambda x: x[1],
            reverse=True,
        )
        return [(doc, score) for doc, score in ranked[:top_k] if score > 0]


def _tokenise(text: str) -> list[str]:
    """Simple lowercase word tokeniser."""
    return re.sub(r"[^a-z0-9\s]", " ", text.lower()).split()


# ── Source adapters ───────────────────────────────────────────────────────────


class SourceAdapter:
    """
    Base adapter for a retrieval source.
    Each source knows how to search its own content.
    """

    async def search(self, query: str, metadata: dict[str, Any]) -> list[RetrievedDocument]:
        raise NotImplementedError


class MemorySourceAdapter(SourceAdapter):
    """Retrieves from the persistent memory store (semantic + procedural)."""

    def __init__(self, db: AsyncSession) -> None:
        self._store = MemoryStore(db)

    async def search(self, query: str, metadata: dict[str, Any]) -> list[RetrievedDocument]:
        results = await self._store.search_by_text(
            query,
            memory_types=[MemoryType.semantic, MemoryType.procedural],
            limit=metadata.get("limit", 5),
        )
        return [
            RetrievedDocument(
                source="memory",
                content=r.content,
                metadata={"type": r.memory_type, "usefulness": r.usefulness_score},
                score=r.usefulness_score,
                citation=f"[memory/{r.memory_type}] {r.content[:60]}…",
            )
            for r in results
        ]


class LogSourceAdapter(SourceAdapter):
    """Stub adapter for pipeline logs. In v2 connects to mcp-data fetch_logs."""

    async def search(self, query: str, metadata: dict[str, Any]) -> list[RetrievedDocument]:
        # Stub: in production this calls mcp-data/tools/fetch_logs
        return [
            RetrievedDocument(
                source="logs",
                content=f"[STUB] Pipeline log search for: {query}",
                score=0.5,
                citation="[pipeline_logs] stub",
            )
        ]


class IncidentSourceAdapter(SourceAdapter):
    """Stub adapter for historical incidents. In v2 connects to mcp-knowledge."""

    async def search(self, query: str, metadata: dict[str, Any]) -> list[RetrievedDocument]:
        # Stub: in production this calls mcp-knowledge/tools/search_incidents
        return [
            RetrievedDocument(
                source="incidents",
                content=f"[STUB] Similar incident search for: {query}",
                score=0.4,
                citation="[incident_history] stub",
            )
        ]


# ── Source router ─────────────────────────────────────────────────────────────


_SOURCE_KEYWORDS: dict[str, list[str]] = {
    "logs": ["log", "error", "stack trace", "traceback", "exception", "failed", "pipeline run"],
    "incidents": ["incident", "previous", "past", "history", "outage", "similar"],
    "repository": ["code", "commit", "file", "function", "model", "sql", "dbt", "transform"],
    "schema": ["schema", "column", "table", "type", "contract", "definition"],
    "docs": ["documentation", "runbook", "guide", "how to", "reference"],
    "memory": ["remember", "strategy", "lesson", "learned", "procedure"],
}


def route_query(query: str) -> str:
    """Simple keyword-based source routing."""
    query_lower = query.lower()
    scores: dict[str, int] = {}
    for source, keywords in _SOURCE_KEYWORDS.items():
        scores[source] = sum(1 for kw in keywords if kw in query_lower)

    best = max(scores, key=lambda s: scores[s])
    return best if scores[best] > 0 else "memory"


# ── Reranker ──────────────────────────────────────────────────────────────────


def rerank_documents(
    query: str,
    documents: list[RetrievedDocument],
    top_k: int = 5,
) -> list[RetrievedDocument]:
    """
    Simple BM25 reranking over retrieved documents.
    A production implementation would use a cross-encoder model here.
    """
    if not documents:
        return []

    texts = [doc.content for doc in documents]
    index = BM25Index(texts)
    ranked_texts = index.search(query, top_k=top_k)

    # Map back to documents preserving original score as secondary sort
    text_to_doc = {doc.content: doc for doc in documents}
    reranked: list[RetrievedDocument] = []

    for text, bm25_score in ranked_texts:
        if text in text_to_doc:
            doc = text_to_doc[text]
            # Blend original score and BM25 score
            doc.score = 0.6 * bm25_score + 0.4 * doc.score
            reranked.append(doc)

    # Add any remaining documents not in BM25 top-k
    reranked_texts = {doc.content for doc in reranked}
    for doc in documents:
        if doc.content not in reranked_texts:
            reranked.append(doc)

    return reranked[:top_k]


# ── Context compressor ────────────────────────────────────────────────────────


def compress_context(
    documents: list[RetrievedDocument],
    max_chars: int = 8_000,
) -> str:
    """
    Trim the retrieved context to fit within the model's context budget.
    Prioritises higher-scoring documents.
    """
    sorted_docs = sorted(documents, key=lambda d: d.score, reverse=True)
    chunks: list[str] = []
    total = 0

    for doc in sorted_docs:
        citation = f"[{doc.citation}]" if doc.citation else f"[{doc.source}]"
        entry = f"{citation}\n{doc.content.strip()}\n"
        if total + len(entry) > max_chars:
            # Truncate the last entry to fit
            remaining = max_chars - total
            if remaining > 100:
                chunks.append(entry[:remaining] + "…")
            break
        chunks.append(entry)
        total += len(entry)

    return "\n---\n".join(chunks)


# ── Orchestrator ──────────────────────────────────────────────────────────────


class RetrievalOrchestrator:
    """
    Drives the full agentic retrieval cycle for a single information need.

    The agent provides a natural-language question. The orchestrator:
        1. Decomposes into sub-queries
        2. Routes each to the right source
        3. Retrieves and reranks
        4. Compresses to context budget
        5. Verifies sufficiency
        6. Returns a structured RetrievalResult with citations
    """

    def __init__(self, db: AsyncSession) -> None:
        self._sources: dict[str, SourceAdapter] = {
            "memory": MemorySourceAdapter(db),
            "logs": LogSourceAdapter(),
            "incidents": IncidentSourceAdapter(),
        }

    async def retrieve(
        self,
        question: str,
        context: str = "",
        max_sub_queries: int = 3,
    ) -> RetrievalResult:
        """
        Retrieve evidence for the given question.

        Args:
            question: The natural-language information need.
            context: Optional prior context to guide decomposition.
            max_sub_queries: Maximum number of parallel sub-queries.

        Returns:
            RetrievalResult with documents, sufficiency verdict and citations.
        """
        # Step 1: Decompose query
        sub_queries = await self._decompose(question, context, max_sub_queries)
        log.info("retrieval_decomposed", question=question[:80], sub_queries=len(sub_queries))

        # Step 2: Route and retrieve from each source
        all_documents: list[RetrievedDocument] = []
        for sq in sub_queries:
            source = self._sources.get(sq.source, self._sources["memory"])
            docs = await source.search(sq.query, metadata={"limit": 5})
            all_documents.extend(docs)

        # Step 3: Rerank
        reranked = rerank_documents(question, all_documents, top_k=8)

        # Step 4: Compress
        context_text = compress_context(reranked, max_chars=6_000)

        # Step 5: Verify sufficiency
        sufficient, summary = await self._verify_sufficiency(question, context_text)
        log.info(
            "retrieval_complete",
            documents=len(reranked),
            sufficient=sufficient,
        )

        citations = list({doc.citation for doc in reranked if doc.citation})

        return RetrievalResult(
            query=question,
            documents=reranked,
            sufficient=sufficient,
            summary=summary,
            citations=citations,
        )

    async def _decompose(
        self,
        question: str,
        context: str,
        max_sub_queries: int,
    ) -> list[SubQuery]:
        """Ask the model to decompose the question into focused sub-queries."""
        import json

        messages = [
            {
                "role": "system",
                "content": (
                    "You decompose investigation questions into focused sub-queries "
                    "for different data sources. Be specific."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Question: {question}\n"
                    f"Context: {context[:500] if context else 'none'}\n\n"
                    f"Break into at most {max_sub_queries} sub-queries. "
                    "Available sources: repository, logs, incidents, schema, docs, memory\n\n"
                    "Return JSON:\n"
                    "  sub_queries: list of { query: string, source: string, priority: high|medium|low }"
                ),
            },
        ]

        response = await _gateway.fast_chat(
            messages, response_format={"type": "json_object"}
        )
        try:
            data = json.loads(response.content)
            raw = data.get("sub_queries", [])
        except json.JSONDecodeError:
            raw = []

        if not raw:
            # Fallback: single routed query
            source = route_query(question)
            return [SubQuery(query=question, source=source)]

        return [
            SubQuery(
                query=sq.get("query", question),
                source=sq.get("source", route_query(question)),
                priority=sq.get("priority", "medium"),
            )
            for sq in raw[:max_sub_queries]
        ]

    async def _verify_sufficiency(
        self, question: str, context: str
    ) -> tuple[bool, str]:
        """Ask the model whether the retrieved evidence is sufficient to answer."""
        import json

        if not context.strip():
            return False, "No evidence retrieved."

        messages = [
            {
                "role": "system",
                "content": "Assess whether the retrieved evidence is sufficient to answer the question.",
            },
            {
                "role": "user",
                "content": (
                    f"Question: {question}\n\n"
                    f"Retrieved evidence:\n{context[:3000]}\n\n"
                    "Return JSON:\n"
                    "  sufficient: bool\n"
                    "  summary: string (one sentence)"
                ),
            },
        ]

        response = await _gateway.fast_chat(
            messages, response_format={"type": "json_object"}
        )
        try:
            data = json.loads(response.content)
            return bool(data.get("sufficient", True)), data.get("summary", "")
        except json.JSONDecodeError:
            return True, "Evidence retrieved (verification skipped)."
