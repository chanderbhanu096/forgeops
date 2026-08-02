# ForgeOps REST API

Base URL: `http://localhost:8000/api/v1` (local development)

All endpoints return JSON. Errors follow the FastAPI default: `{"detail": "message"}`.

---

## Missions

### Create a mission

```http
POST /missions
Content-Type: application/json

{
  "title": "Repair revenue pipeline",
  "description": "The customer analytics pipeline is failing...",
  "max_steps": 50,
  "max_cost_usd": 2.0,
  "max_duration_seconds": 600
}
```

Response `201`:
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "title": "Repair revenue pipeline",
  "status": "pending",
  "current_state": null,
  "cost_usd_used": 0.0,
  "steps_used": 0,
  "created_at": "2025-01-15T10:30:00Z"
}
```

---

### List missions

```http
GET /missions?status=running&limit=20&offset=0
```

Response `200`: array of mission objects.

---

### Get mission

```http
GET /missions/{id}
```

Response `200`: full mission object including `checkpoint` and `result`.

---

### Start a mission

```http
POST /missions/{id}/start
```

Begins autonomous execution. Returns `200 {"status": "started"}`.

The agent runs asynchronously. Stream progress via SSE (see below).

---

### Pause a mission

```http
POST /missions/{id}/pause
```

Suspends execution after the current state handler completes. Returns `200 {"status": "paused"}`.

---

### Resume a mission

```http
POST /missions/{id}/resume
```

Resumes from the last completed state. Returns `200 {"status": "resumed"}`.

---

## Live streaming (SSE)

```http
GET /stream/{mission_id}
Accept: text/event-stream
```

Returns a Server-Sent Events stream. Each event is a JSON object:

```
event: state_transition
data: {"from": "evidence_collection", "to": "hypothesis_creation", "cost_usd": 0.03}

event: tool_call
data: {"server": "github", "tool": "read_file", "duration_ms": 145, "success": true}

event: budget_update
data: {"steps_used": 12, "cost_usd_used": 0.18, "elapsed_seconds": 47}

event: completed
data: {"result": {...}}
```

---

## Approvals

### List pending approvals

```http
GET /approvals?decision=pending
```

---

### Get approval

```http
GET /approvals/{id}
```

Response includes `summary`, `diff` (unified diff), `evidence` and `risk_level`.

---

### Submit approval decision

```http
POST /approvals/{id}/decide
Content-Type: application/json

{
  "decision": "approved",
  "notes": "LGTM — verified the lineage impact manually"
}
```

`decision` must be `approved` or `rejected`. Once approved, the agent proceeds to `EXECUTION`.

---

## Skills

### List skills

```http
GET /skills
```

Response: array of skill metadata (name, version, description, permissions).

---

### Get skill

```http
GET /skills/{name}
```

Returns the full skill definition including required tools and I/O schema.

---

## Memory

### Search memory

```http
GET /memory?query=partition+error&memory_type=procedural&limit=10
```

`memory_type`: `episodic` | `semantic` | `procedural` | `feedback`

---

### Get mission memory

```http
GET /memory/mission/{mission_id}
```

Returns all memory entries created during a specific mission.

---

## Observability

### Health check

```http
GET /health
```

Response `200`: `{"status": "ok"}`

---

### Prometheus metrics

```http
GET /metrics
```

Returns Prometheus text format (0.0.4). Scrape this endpoint from your Prometheus instance.

Metrics:
- `forgeops_missions_total{status}` — lifetime count by mission status
- `forgeops_missions_active` — currently running missions
- `forgeops_model_cost_usd_total` — cumulative LLM spend
- `forgeops_tool_calls_total{server,tool}` — MCP tool invocations
- `forgeops_verifier_runs_total{pipeline,passed}` — verification pipeline executions
- `forgeops_approvals_pending` — approvals awaiting human decision

---

## Interactive API docs

Swagger UI is available at `http://localhost:8000/docs` when `ENVIRONMENT != production`.
