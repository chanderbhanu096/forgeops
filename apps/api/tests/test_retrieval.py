"""Tests for agentic retrieval."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from forgeops.retrieval.orchestrator import (
    BM25Index,
    RetrievedDocument,
    SubQuery,
    compress_context,
    rerank_documents,
    route_query,
)


# ── BM25Index ─────────────────────────────────────────────────────────────────


def test_bm25_returns_relevant_document():
    docs = [
        "revenue pipeline failed with column error",
        "airflow DAG completed successfully",
        "currency conversion factor changed from eur to cents",
    ]
    index = BM25Index(docs)
    results = index.search("revenue column failure", top_k=2)
    assert len(results) >= 1
    # The first result should be the most relevant
    assert "revenue" in results[0][0].lower() or "column" in results[0][0].lower()


def test_bm25_returns_empty_for_no_match():
    docs = ["completely unrelated document about weather"]
    index = BM25Index(docs)
    # BM25 returns 0-score results for totally unrelated queries
    results = index.search("revenue pipeline error", top_k=3)
    # All scores should be 0 — filtered out
    assert all(score == 0 for _, score in results)


def test_bm25_respects_top_k():
    docs = [f"document about pipeline {i}" for i in range(20)]
    index = BM25Index(docs)
    results = index.search("pipeline", top_k=5)
    assert len(results) <= 5


# ── Source router ─────────────────────────────────────────────────────────────


def test_route_query_logs():
    source = route_query("check the error log from the failed pipeline run")
    assert source == "logs"


def test_route_query_incidents():
    source = route_query("find previous similar incidents in the history")
    assert source == "incidents"


def test_route_query_repository():
    source = route_query("look at the dbt model code and sql transformation")
    assert source == "repository"


def test_route_query_memory():
    source = route_query("what did we learn and what lesson can we remember from this strategy")
    assert source == "memory"


def test_route_query_falls_back_to_memory():
    source = route_query("this is a completely ambiguous question")
    assert source == "memory"   # fallback


# ── Reranker ──────────────────────────────────────────────────────────────────


def test_rerank_returns_most_relevant_first():
    docs = [
        RetrievedDocument(source="logs", content="revenue column error in dbt model", score=0.3),
        RetrievedDocument(source="docs", content="general airflow documentation", score=0.8),
        RetrievedDocument(source="incidents", content="past revenue pipeline failure", score=0.5),
    ]
    reranked = rerank_documents("revenue column failure", docs, top_k=3)
    assert len(reranked) <= 3
    # revenue-related documents should rank above the general airflow doc
    revenue_positions = [
        i for i, d in enumerate(reranked) if "revenue" in d.content.lower()
    ]
    general_positions = [
        i for i, d in enumerate(reranked) if "airflow documentation" in d.content.lower()
    ]
    if revenue_positions and general_positions:
        assert min(revenue_positions) < min(general_positions)


def test_rerank_empty_input():
    result = rerank_documents("any query", [], top_k=5)
    assert result == []


def test_rerank_respects_top_k():
    docs = [
        RetrievedDocument(source="s", content=f"document {i}", score=float(i) / 10)
        for i in range(20)
    ]
    reranked = rerank_documents("document", docs, top_k=5)
    assert len(reranked) <= 5


# ── Context compressor ────────────────────────────────────────────────────────


def test_compress_context_respects_limit():
    docs = [
        RetrievedDocument(source="logs", content="A" * 3000, score=0.9, citation="[logs]"),
        RetrievedDocument(source="docs", content="B" * 3000, score=0.8, citation="[docs]"),
    ]
    compressed = compress_context(docs, max_chars=2000)
    assert len(compressed) <= 2200   # small tolerance for separators


def test_compress_context_includes_citations():
    docs = [
        RetrievedDocument(
            source="incidents",
            content="Revenue dropped after column rename",
            score=0.9,
            citation="[INC-2023-0441]",
        )
    ]
    compressed = compress_context(docs, max_chars=5000)
    assert "INC-2023-0441" in compressed


def test_compress_context_empty_returns_empty():
    compressed = compress_context([], max_chars=5000)
    assert compressed == ""


# ── RetrievalOrchestrator ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_orchestrator_returns_result(db_session):
    """Orchestrator returns a RetrievalResult with documents and citations."""
    from forgeops.retrieval.orchestrator import RetrievalOrchestrator, SubQuery

    with patch(
        "forgeops.retrieval.orchestrator.RetrievalOrchestrator._decompose",
        new_callable=AsyncMock,
    ) as mock_decompose, patch(
        "forgeops.retrieval.orchestrator.RetrievalOrchestrator._verify_sufficiency",
        new_callable=AsyncMock,
    ) as mock_verify:
        mock_decompose.return_value = [
            SubQuery(query="revenue column error", source="memory", priority="high")
        ]
        mock_verify.return_value = (True, "Evidence is sufficient.")

        orchestrator = RetrievalOrchestrator(db_session)
        result = await orchestrator.retrieve(
            question="Why did the revenue pipeline fail?",
            context="dbt pipeline on AWS",
        )

    assert result.query == "Why did the revenue pipeline fail?"
    assert result.sufficient is True
    assert result.summary == "Evidence is sufficient."


@pytest.mark.asyncio
async def test_orchestrator_falls_back_when_decompose_empty(db_session):
    """When decompose returns nothing, falls back to a single routed query."""
    from forgeops.retrieval.orchestrator import RetrievalOrchestrator

    with patch(
        "forgeops.retrieval.orchestrator.RetrievalOrchestrator._decompose",
        new_callable=AsyncMock,
    ) as mock_decompose, patch(
        "forgeops.retrieval.orchestrator.RetrievalOrchestrator._verify_sufficiency",
        new_callable=AsyncMock,
    ) as mock_verify:
        mock_decompose.return_value = []   # no sub-queries
        mock_verify.return_value = (False, "Insufficient evidence.")

        orchestrator = RetrievalOrchestrator(db_session)
        result = await orchestrator.retrieve("Find error in logs")

    # Should still return a result, not raise
    assert result is not None
    assert result.sufficient is False
