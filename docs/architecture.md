# ForgeOps Architecture — Deep Dive

This document explains the internal design of each system in enough detail to understand, extend or debug it.

---

## Table of contents

1. [Agent runtime](#1-agent-runtime)
2. [Model gateway](#2-model-gateway)
3. [Skill registry](#3-skill-registry)
4. [MCP tool ecosystem](#4-mcp-tool-ecosystem)
5. [Verifier-first execution](#5-verifier-first-execution)
6. [Multi-agent review pipeline](#6-multi-agent-review-pipeline)
7. [Agentic retrieval](#7-agentic-retrieval)
8. [Operational memory](#8-operational-memory)
9. [Observability](#9-observability)
10. [Database schema](#10-database-schema)

---

## 1. Agent runtime

**File**: `apps/api/forgeops/agent/runtime.py`

The runtime is a persistent finite state machine. Each mission is a row in the `missions` table with a `current_state` column. When `run_mission()` is called:

1. The current state is read from the database.
2. Budget checks run (steps, cost USD, elapsed seconds).
3. If the mission is paused, the coroutine suspends.
4. The handler for the current state is called.
5. The handler returns the next state.
6. `_transition()` writes the new state atomically and appends a `StateTransition` row.
7. SSE events are emitted for the UI.
8. The loop continues until `completed` or `failed`.

### Transition table

```python
TRANSITIONS = {
    None:                           [mission_received],
    mission_received:               [environment_discovery, failed],
    environment_discovery:          [plan_generation, failed],
    plan_generation:                [evidence_collection, failed],
    evidence_collection:            [hypothesis_creation, failed],
    hypothesis_creation:            [hypothesis_verification, failed],
    hypothesis_verification:        [solution_generation, failed],
    solution_generation:            [sandbox_execution, failed],
    sandbox_execution:              [test_and_review, failed],
    test_and_review:                [human_approval, failed],
    human_approval:                 [execution, failed],   # gated on DB flag
    execution:                      [post_action_monitoring, failed],
    post_action_monitoring:         [completed, failed],
}
```

Any transition not in this map raises `InvalidTransitionError`. This makes the workflow **deterministic** — the agent cannot jump to an arbitrary state.

### Checkpointing

`MissionContext` serialises itself to a JSON-compatible dict on every transition. The checkpoint is stored in `missions.checkpoint`. On startup (or resume after pause), `_from_checkpoint()` restores full context including hypotheses, plans, evidence and the top hypothesis.

### Budget gates

Three independent budget checks run before each state handler:
- `steps_used >= max_steps` → fail with `budget_exceeded_steps`
- `cost_usd_used >= max_cost_usd` → fail with `budget_exceeded_cost`
- `elapsed_seconds >= max_duration_seconds` → fail with `budget_exceeded_time`

Budgets are configurable per-mission via the API. Defaults: 50 steps, $2.00, 600 seconds.

---

## 2. Model gateway

**File**: `apps/api/forgeops/agent/gateway.py`

A thin wrapper around OpenAI and Anthropic SDKs that:
- Routes to OpenAI gpt-4o by default
- Falls back to Anthropic claude-3-5-sonnet on OpenAI errors
- Tracks prompt tokens, completion tokens and cost per call
- Emits a Langfuse generation trace after every call
- Returns a `ModelResponse` dataclass with content, tokens and cost

Cost is computed from published token prices embedded in the gateway. The `mission_context.total_cost_usd` is incremented after each call so budget checks remain accurate.

---

## 3. Skill registry

**File**: `apps/api/forgeops/skills/registry.py`

Skills are YAML files in `skills/definitions/`. The registry:
1. Loads all `.yaml` files at startup.
2. Sorts multiple versions of the same skill by semver (highest first).
3. Validates required fields with Pydantic.
4. Exposes `get(name)` → latest version, `get(name, version)` → exact version.
5. Exposes `find_for_task(description)` → scored list of relevant skills.

### Skill schema

```yaml
name: string              # snake_case, unique
version: string           # semver x.y.z
description: string       # used for skill discovery scoring
required_tools: list      # MCP tool identifiers the skill needs
permissions:
  filesystem: sandbox_only | any
  database: read_only | read_write
  network: restricted | any
inputs: dict              # name → type string
outputs: dict             # name → type string
dependencies: list        # other skill names required before this one
```

---

## 4. MCP tool ecosystem

**Files**: `services/mcp-github/`, `services/mcp-data/`, `services/mcp-knowledge/`

Each MCP server is an independent FastAPI application. The agent calls them over HTTP. All calls are authenticated with a shared `MCP_SECRET` header.

### Request format

```json
{
  "tool": "read_file",
  "arguments": {
    "repository": "org/repo",
    "path": "models/revenue.sql",
    "ref": "main"
  }
}
```

### Response format

```json
{
  "tool": "read_file",
  "result": { ... },
  "error": null,
  "duration_ms": 142
}
```

### Tool call audit

Every tool invocation is persisted as a `ToolCall` row in PostgreSQL with:
- Input arguments (sanitised — secrets stripped)
- Output summary
- Status (pending → running → succeeded/failed/blocked)
- Duration in milliseconds

This provides a complete, queryable audit trail of every action the agent took.

---

## 5. Verifier-first execution

**Files**: `apps/api/forgeops/verification/`

### Code verifier chain (`verify_patch`)

| Verifier | What it checks | Severity on fail |
|---|---|---|
| `PatchSyntaxVerifier` | `ast.parse` each changed Python file | critical |
| `DangerousPatternVerifier` | `os.system`, `eval`, `exec`, hardcoded secrets | critical/high |
| `ImportVerifier` | `subprocess` blocked; `requests` flagged | critical/medium |
| `PatchSizeVerifier` | Rejects patches > 500 lines (signals LLM hallucination) | medium |

### SQL verifier chain (`verify_sql`) — fast-fail enabled

| Verifier | What it checks |
|---|---|
| `SQLStatementTypeVerifier` | Blocks DELETE, DROP, TRUNCATE, INSERT, UPDATE |
| `SQLInjectionVerifier` | Stacked queries, LOAD FILE, INTO OUTFILE |
| `SQLRowLimitVerifier` | Requires LIMIT clause |
| `SQLRiskVerifier` | SELECT *, CROSS JOIN — informational only |

### Terraform verifier chain (`verify_terraform`)

| Verifier | What it checks |
|---|---|
| `TerraformDestructiveChangeVerifier` | `force_destroy = true`, `prevent_destroy = false` |
| `TerraformSecurityVerifier` | Open security groups (0.0.0.0/0), IAM wildcard policies |

### Findings

Each verifier returns a list of `Finding` objects:
```python
@dataclass(frozen=True)
class Finding:
    verifier: str
    severity: Severity   # info | low | medium | high | critical
    title: str
    detail: str
    location: str | None  # file:line if known
```

A `PipelineResult` aggregates all findings across the chain. The `passed` flag is `True` only if no verifier failed. Critical findings in fast-fail mode short-circuit the remaining chain.

After every pipeline run, `trace_verification()` emits an OTEL span and structured log with critical/high counts.

---

## 6. Multi-agent review pipeline

**File**: `apps/api/forgeops/agent/multi_agent.py`

```
run_review_pipeline(context)
    │
    ├── builder_agent(context) → patch v1
    │
    ├── for cycle in range(MAX_REVISION_CYCLES=3):
    │       reviewer_agent(patch) → ReviewerOutput
    │       if approved: break
    │       builder_agent(context, reviewer_comments) → patch vN
    │
    ├── security_agent(patch) → SecurityOutput
    │   if blocked: return failed MultiAgentResult
    │
    ├── verifier_agent(patch) → VerifierOutput (runs VerificationPipeline)
    │   if not passed: return failed MultiAgentResult
    │
    └── judge_agent(context, patch, reviewer, security, verifier)
            → JudgeOutput with accept/reject + reasoning
```

Each agent is a pure async function that receives the current context and returns a typed dataclass. The orchestrator drives the loop. Agents do not call each other directly — only the orchestrator does.

`MultiAgentResult` is attached to `MissionContext.multi_agent_result` and persisted in the mission checkpoint. The approval gate reads `judge_output.accept` to determine whether to surface the PR to humans.

---

## 7. Agentic retrieval

**File**: `apps/api/forgeops/retrieval/orchestrator.py`

The retrieval system is activated during `EVIDENCE_COLLECTION`. It is not a static RAG pipeline — the agent decides what to retrieve and whether the evidence is sufficient.

### Components

**`BM25Index`** — sparse keyword retrieval over in-memory documents. Documents are added via `add_document(content, metadata)`. `search(query, top_k)` returns scored results.

**`SourceRouter`** — routes a query to the appropriate source(s): `repository`, `logs`, `documentation`, `incidents`, `database_schema`, `lineage`, `general`. Routing is keyword-based with fallback to `general`.

**`Reranker`** — cross-encoder style reranking. Scores each candidate by computing token overlap between the query and document content. Returns top-k results sorted by relevance.

**`ContextCompressor`** — trims the retrieved evidence to fit within a token budget while preserving the most relevant sections. Appends source citations.

**`RetrievalOrchestrator`** — the entry point. Given a list of queries:
1. Decomposes each query into sub-queries.
2. Routes each sub-query to a source.
3. Retrieves candidates from each source.
4. Reranks the combined pool.
5. Compresses to a context window budget.
6. Checks sufficiency: `relevant_count / total_results >= 0.3`.
7. Returns a `RetrievalResult` with compressed context and citations.

---

## 8. Operational memory

**File**: `apps/api/forgeops/memory/store.py`

Memory entries are rows in the `memory_entries` table. Each entry has:
- `memory_type`: episodic | semantic | procedural | feedback
- `mission_id`: which mission created this entry
- `content`: the text content
- `embedding`: pgvector embedding (for similarity search in production)
- `relevance_score`: float, updated by feedback
- `extra`: JSON metadata

### `MemoryStore`

```python
store = MemoryStore(session)

await store.add(mission_id, MemoryType.episodic, "Revenue pipeline failed due to unit change")
await store.add(mission_id, MemoryType.procedural, "Check Glue metadata for Athena partition errors")

results = await store.search(query="partition error", memory_type=MemoryType.procedural, limit=5)
```

### `MissionMemoryWriter`

Called automatically at the end of `POST_ACTION_MONITORING`. Writes:
- One episodic entry summarising the mission outcome
- Procedural entries from each step that succeeded
- Feedback entries from human approval decisions

---

## 9. Observability

**File**: `apps/api/forgeops/observability.py`

### OpenTelemetry

`setup_otel()` is called at application startup. If `OTEL_EXPORTER_OTLP_ENDPOINT` is set, it creates a `TracerProvider` with `BatchSpanProcessor` and exports to your OTEL collector (Grafana Tempo, Jaeger, etc.).

Three instrumentation helpers:
- `trace_state_transition(mission_id, from_state, to_state)` — emits a span per state change
- `trace_tool_call(mission_id, server, tool, duration_ms, success)` — emits a span per MCP call
- `trace_verification(pipeline, passed, critical_count, high_count, total_findings)` — emits a span per verifier pipeline run

All helpers degrade gracefully when OTEL is not configured.

### Langfuse

`LangfuseTracer` wraps the Langfuse SDK. If `LANGFUSE_PUBLIC_KEY` is set, each model gateway call creates a `generation` trace with model name, token counts, cost, latency and provider. The tracer flushes on application shutdown.

### Prometheus

`GET /metrics` returns metrics in Prometheus text format (0.0.4):

```
forgeops_missions_total{status="running"} 3
forgeops_missions_active 3
forgeops_model_cost_usd_total 1.47
forgeops_tool_calls_total{server="github",tool="read_file"} 42
forgeops_verifier_runs_total{pipeline="patch",passed="true"} 18
forgeops_approvals_pending 1
```

All values are computed from ORM queries — no in-process counter state.

### Structured logging

`structlog` is configured in `forgeops/logging.py`. Every log event is a JSON object in production and a coloured key-value string in development. Key fields: `mission_id`, `state`, `handler`, `duration_ms`, `cost_usd`.

---

## 10. Database schema

**File**: `apps/api/forgeops/models/orm.py`

```
missions
  id, title, description, status, current_state
  max_steps, steps_used, max_cost_usd, cost_usd_used, max_duration_seconds
  checkpoint (JSONB), attachments (JSONB), result (JSONB), error
  created_at, updated_at, completed_at

state_transitions                    ← immutable audit log
  id (BigInt), mission_id, from_state, to_state
  handler_output (JSONB), cost_usd, created_at

tool_calls
  id, mission_id, tool_name, server
  status (pending|running|succeeded|failed|blocked)
  input (JSONB), output (JSONB), error
  duration_ms, tokens_used, created_at, completed_at

skills
  id, name, version, description
  definition (JSONB), is_active, created_at

memory_entries
  id, mission_id, memory_type (episodic|semantic|procedural|feedback)
  content, embedding (vector), relevance_score
  extra (JSONB), created_at

approvals
  id, mission_id, summary, diff (text), evidence (JSONB)
  risk_level, decision (pending|approved|rejected|auto_approved)
  reviewer_id, reviewer_notes, created_at, decided_at
```

### Cross-database type adapters

The ORM uses `TypeDecorator` wrappers so the same models work on both PostgreSQL (production) and SQLite (tests):

| Adapter | PostgreSQL | SQLite |
|---|---|---|
| `_JSONB` | `JSONB` | `JSON` |
| `_UUID` | `UUID` | `String(36)` |
| pgvector | `Vector(1536)` | `JSON` (disabled) |
| `BigInteger` id | `BigInteger` | `Integer` |
