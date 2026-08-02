<div align="center">

# ⚙️ ForgeOps AI

### A policy-controlled autonomous AI data and cloud engineer

*Not a chatbot. Not a copilot. A goal-driven AI worker operating inside a controlled engineering environment.*

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=flat&logo=nextdotjs&logoColor=white)](https://nextjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Tests](https://img.shields.io/badge/tests-98%20passing-22c55e?style=flat)](#running-tests)
[![License](https://img.shields.io/badge/license-MIT-6366f1?style=flat)](LICENSE)

</div>

---

## What is ForgeOps?

You give it a **mission**:

```
"The customer analytics pipeline is failing.
 Find the root cause, repair it, test the fix, and open a pull request."
```

ForgeOps then works autonomously — inspecting your repository, reading logs, querying the warehouse, writing and testing a code fix, reviewing its own changes with a security agent, and submitting a pull request. **It pauses for your approval before touching production.** If validation fails after deployment, it rolls back automatically.

That is not a chatbot. It is an **AI operations engineer** running inside a controlled, audited environment.

---

## Mission Control UI

```
┌─────────────────────────────────────────────────────────────────┐
│  ForgeOps Mission Control                          ● LIVE       │
├─────────────────────────────────────────────────────────────────┤
│  Mission: Repair failed customer revenue pipeline               │
│  Status: ████████████████████░░░░░  VALIDATING FIX  71%        │
├──────────────────────────┬──────────────────────────────────────┤
│  Execution Graph         │  Current Activity                   │
│                          │                                      │
│  ✓ Understand mission    │  Running dbt integration tests       │
│  ✓ Inspect repository    │                                      │
│  ✓ Analyse logs          │  38 / 42 tests passed               │
│  ✓ Query warehouse       │  2  failed                          │
│  ✓ Find root cause       │  2  still running                   │
│  ✓ Generate fix          │                                      │
│  ◉ Validate fix          │  Estimated cost so far: €0.17       │
│  ○ Security review       │                                      │
│  ○ Create PR             │  Steps: 23/50  │  Time: 4m 12s      │
└──────────────────────────┴──────────────────────────────────────┘
```

Additional screens: live execution trace · repository diff viewer · terminal & tool-call timeline · evidence explorer · agent memory · approval centre · security findings · model cost dashboard · historical mission replay.

---

## The demo mission

> "Yesterday's deployment caused the executive revenue dashboard to show 18% lower revenue. Investigate, identify affected datasets, produce a safe fix, and open a pull request."

ForgeOps discovers:

1. A source column changed from **euros → cents** after a schema migration.
2. The schema remained technically valid — existing unit tests **passed**.
3. A dbt transformation applied the old conversion factor.
4. The error propagated through **3 downstream models**.
5. **2 dashboards** and **1 ML feature** were affected.

It then:
- Generates a lineage impact graph
- Finds the offending Git commit
- Writes a regression test that would have caught it
- Corrects the transformation
- Runs the pipeline in a sandbox
- Compares repaired values against historical distribution ranges
- Produces a backfill plan
- Opens a draft pull request
- Waits for your approval before touching production

---

## Seven core systems

### 1 · Autonomous agent runtime

A durable 13-state machine persisted to PostgreSQL. Every transition is:
- Written atomically before the handler runs (crash-safe)
- Appended to an immutable audit log
- Subject to **step, cost and time budgets**
- Resumable after crash or intentional pause

```
MISSION_RECEIVED → ENVIRONMENT_DISCOVERY → PLAN_GENERATION
→ EVIDENCE_COLLECTION → HYPOTHESIS_CREATION → HYPOTHESIS_VERIFICATION
→ SOLUTION_GENERATION → SANDBOX_EXECUTION → TEST_AND_REVIEW
→ HUMAN_APPROVAL → EXECUTION → POST_ACTION_MONITORING
```

Supports: pause/resume · failure recovery · checkpointing · parallel tool execution · automatic rollback on post-deployment validation failure.

---

### 2 · Dynamic skill system

Each capability is a versioned YAML skill — not a hardcoded prompt:

```yaml
name: dbt_model_repair
version: 1.0.0

description: >
  Diagnose and repair failing dbt models.

required_tools:
  - repository.read
  - repository.patch
  - dbt.compile
  - dbt.test

permissions:
  filesystem: sandbox_only
  database: read_only
  network: restricted

outputs:
  root_cause: string
  changed_files: list[string]
  confidence: float
```

Built-in skills: `dbt_model_repair` · `log_investigation` · `data_lineage_analysis` · `pull_request_creation` · `security_review`

Skills support: discovery · semver versioning · permission validation · dependency resolution · evaluation · rollback · registry.

---

### 3 · MCP-based tool ecosystem

Three custom HTTP MCP servers provide the agent's hands:

| MCP Server | Tools |
|---|---|
| **GitHub** | read_file, create_branch, apply_patch, create_pull_request, get_ci_results |
| **Data Platform** | inspect_pipeline_runs, fetch_logs, run_read_only_sql, get_lineage, run_data_quality_tests |
| **Knowledge** | search_runbooks, find_incident_history, get_architecture_decisions, search_docs |

All tool calls pass through an MCP gateway with auth, audit logging, permission checks and sandbox isolation.

---

### 4 · Verifier-first execution

**The model is not trusted because its answer sounds correct. It is trusted when a deterministic test proves it is correct.**

Every generated output passes a multi-stage verifier before reaching the approval gate:

```
Generated patch
     ↓
Syntax check (ast.parse)
     ↓
Dangerous pattern scan (os.system, eval, hardcoded secrets)
     ↓
Import policy (subprocess blocked, requests flagged)
     ↓
Patch size gate
     ↓
Unit + integration tests
     ↓
Security scan (Semgrep / Checkov patterns)
     ↓
Policy validation
     ↓
Sandbox execution
```

SQL and Terraform go through equivalent purpose-built verifier chains.

---

### 5 · Multi-agent review pipeline

Four specialised agents with non-overlapping responsibilities:

```
Builder creates patch
       ↓
Reviewer requests changes (up to 3 cycles)
       ↓
Builder revises patch
       ↓
Security agent: injection, secrets, permissions, dangerous commands
       ↓
Verifier: deterministic test execution
       ↓
Judge: does the solution meet the mission's acceptance criteria?
       ↓
Human approval gate
```

---

### 6 · Agentic retrieval

RAG is an internal capability — not the product. The agent decides:

- **What** it needs to know
- **Which source** should contain the answer
- **Whether the evidence is sufficient** or whether to search again
- Whether sources conflict, and how to resolve that

Sources: repository code · git history · pipeline logs · data contracts · incident history · database schemas · lineage graphs · CI/CD results.

Pipeline: query decomposition → source routing → dense + sparse retrieval → reranking → evidence verification → context compression → citation generation.

---

### 7 · Operational memory

Persisted across missions using pgvector similarity search:

| Memory type | Example |
|---|---|
| **Episodic** | What happened in the June revenue incident |
| **Semantic** | "This repository requires Python 3.11" |
| **Procedural** | "For Athena partition mismatches, check Glue metadata first" |
| **Feedback** | Human accepted root cause · human rejected patch · deployment fixed incident |

The system can propose updated instructions, new skill versions or new evaluation cases — but changes require human review and evaluation pass.

---

## Architecture overview

```
                   ┌──────────────────────────────┐
                   │      Mission Control UI       │
                   │  Goals · traces · diffs ·     │
                   │  approvals · evaluations      │
                   └─────────────┬────────────────┘
                                 │ SSE / REST
                   ┌─────────────▼────────────────┐
                   │        Agent Runtime          │
                   │  State machine · budgets ·    │
                   │  checkpoints · recovery       │
                   └──────┬──────────────┬─────────┘
                          │              │
             ┌────────────▼────┐  ┌──────▼──────────────┐
             │ Skill Registry  │  │   Model Gateway      │
             │ Discovery ·     │  │   OpenAI primary     │
             │ versioning ·    │  │   Anthropic fallback │
             │ permissions     │  │   Cost controls      │
             └────────┬────────┘  └─────────────────────┘
                      │
                ┌─────▼──────────────────────────────┐
                │           MCP Gateway               │
                │  Auth · policies · audit · sandbox  │
                └──┬──────────────┬──────────────┬───┘
                   │              │               │
             ┌─────▼──┐   ┌───────▼───┐   ┌──────▼──────┐
             │ GitHub │   │   Data    │   │  Knowledge  │
             │  MCP   │   │   MCP     │   │    MCP      │
             └────────┘   └───────────┘   └─────────────┘

    ┌────────────────────────────────────────────────────────┐
    │    Verification · Security · Evaluation platform       │
    │    Tests · policy checks · judges · tracing            │
    └────────────────────────────────────────────────────────┘

    ┌────────────────────────────────────────────────────────┐
    │            PostgreSQL (pgvector) + Redis               │
    │    Missions · state transitions · memory · skills      │
    └────────────────────────────────────────────────────────┘
```

---

## Quick start (5 minutes)

### Prerequisites

- Docker Desktop (or Docker + Docker Compose v2)
- An OpenAI API key

### 1. Clone

```bash
git clone https://github.com/chanderbhanu096/forgeops.git
cd forgeops
```

### 2. Configure

```bash
cp .env.example .env
```

Open `.env` and set your `OPENAI_API_KEY`. Everything else has working defaults for local development.

### 3. Start

```bash
docker compose up -d
```

This starts: PostgreSQL 16 with pgvector · Redis 7 · the API server · the Mission Control UI · all three MCP servers · the sandbox executor.

First build takes ~3 minutes. Subsequent starts take ~15 seconds.

### 4. Open

| URL | What it is |
|---|---|
| http://localhost:3000 | Mission Control UI |
| http://localhost:8000/docs | Interactive API docs (Swagger) |
| http://localhost:8000/metrics | Prometheus metrics |

### 5. Submit a mission

Open Mission Control, click **New Mission**, and type:

```
Investigate why the customer revenue pipeline is reporting 18% lower 
revenue after yesterday's deployment. Find the root cause and create 
a pull request with the fix.
```

Watch the execution graph update in real time.

---

## Running tests

```bash
cd apps/api

# Install dependencies (one-time)
pip install poetry
poetry install

# Run all tests
PYTHONPATH=. pytest tests/ -v

# Run a specific module
PYTHONPATH=. pytest tests/test_agent_runtime.py -v

# Run the demo integration test
PYTHONPATH=. pytest tests/demo/ -v
```

**98 tests, 0 failures.**

Test coverage: agent runtime · state machine transitions · model gateway · skill registry · verification pipeline (code, SQL, terraform) · multi-agent orchestration · agentic retrieval · memory store · missions API · approvals API · Prometheus metrics · demo integration scenario.

---

## Project structure

```
forgeops/
├── .env.example                      ← copy to .env, set OPENAI_API_KEY
├── docker-compose.yml                ← one command local stack
│
├── apps/
│   ├── api/                          ← FastAPI agent runtime
│   │   └── forgeops/
│   │       ├── agent/
│   │       │   ├── runtime.py        ← 13-state durable state machine
│   │       │   ├── handlers.py       ← one async handler per state
│   │       │   ├── gateway.py        ← OpenAI + Anthropic with fallback
│   │       │   ├── context.py        ← mission context, checkpointing
│   │       │   └── multi_agent.py    ← Builder→Reviewer→Security→Judge
│   │       ├── skills/
│   │       │   ├── registry.py       ← YAML loader, semver sort
│   │       │   └── definitions/      ← 5 built-in skill YAMLs
│   │       ├── verification/
│   │       │   ├── pipeline.py       ← orchestrates verifier chains
│   │       │   ├── code_verifiers.py ← syntax, dangerous patterns, imports
│   │       │   ├── sql_verifiers.py  ← injection, row limits, risk
│   │       │   └── infra_verifiers.py← terraform destructive + security
│   │       ├── retrieval/
│   │       │   └── orchestrator.py   ← BM25, source router, reranker
│   │       ├── memory/
│   │       │   └── store.py          ← episodic, semantic, procedural, feedback
│   │       ├── models/orm.py         ← SQLAlchemy ORM (cross-DB type adapters)
│   │       ├── observability.py      ← OpenTelemetry + Langfuse
│   │       └── api/routes/           ← missions, approvals, skills, memory, SSE
│   │
│   └── web/                          ← Next.js 14 Mission Control UI
│       └── src/
│           ├── app/                  ← mission list, detail, approvals, memory
│           ├── components/           ← ExecutionGraph, DiffViewer, BudgetMeter
│           └── lib/                  ← API client, SSE hook
│
├── services/
│   ├── mcp-github/main.py            ← GitHub MCP server (port 8001)
│   ├── mcp-data/main.py              ← Data platform MCP server (port 8002)
│   └── mcp-knowledge/main.py         ← Knowledge MCP server (port 8003)
│
├── infra/
│   ├── aws/                          ← Terraform: ECS Fargate + RDS + ElastiCache
│   │   └── modules/vpc,ecr,rds,alb,ecs-service,elasticache/
│   └── azure/                        ← Terraform: Container Apps + Postgres + Redis
│       └── modules/acr,postgres,redis,keyvault/
│
└── .github/workflows/ci-cd.yml       ← test → build → deploy (AWS or Azure)
```

---

## Technology stack

| Layer | Technology |
|---|---|
| **API runtime** | Python 3.11, FastAPI, SQLAlchemy async, Pydantic v2 |
| **Primary LLM** | OpenAI gpt-4o |
| **Fallback LLM** | Anthropic claude-3-5-sonnet |
| **State / cache** | PostgreSQL 16 + pgvector, Redis 7 |
| **Retrieval** | BM25 sparse + dense vectors, cross-encoder reranking |
| **MCP servers** | Custom HTTP servers — GitHub, Data, Knowledge |
| **Verification** | ast, Ruff patterns, Semgrep/Checkov rules |
| **Frontend** | Next.js 14, TypeScript, SSE for live updates |
| **Observability** | OpenTelemetry, Langfuse (LLM traces), structlog |
| **Infra — AWS** | ECS Fargate, RDS, ElastiCache, ALB, ECR, Terraform |
| **Infra — Azure** | Container Apps, PostgreSQL Flexible Server, Redis, ACR, Terraform |
| **CI/CD** | GitHub Actions — test → build matrix → conditional cloud deploy |

---

## Deployment

Full step-by-step instructions for both clouds in [DEPLOYMENT.md](DEPLOYMENT.md).

**AWS (ECS Fargate)**
```bash
cd infra/aws
cp terraform.tfvars.example terraform.tfvars   # fill in your values
terraform init && terraform apply
```

**Azure (Container Apps)**
```bash
cd infra/azure
cp terraform.tfvars.example terraform.tfvars
terraform init && terraform apply
```

---

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | **Yes** | Primary LLM — gpt-4o |
| `ANTHROPIC_API_KEY` | No | Fallback LLM |
| `DATABASE_URL` | Yes (auto in Docker) | PostgreSQL async connection string |
| `REDIS_URL` | Yes (auto in Docker) | Redis connection string |
| `MCP_SECRET` | Yes (auto in Docker) | Shared auth token for MCP servers |
| `GITHUB_TOKEN` | No | GitHub API — required for PR creation |
| `LANGFUSE_PUBLIC_KEY` | No | LLM trace observability |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | No | OTEL traces → Grafana Tempo etc. |
| `ENVIRONMENT` | No | `development` / `staging` / `production` |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Licence

MIT — see [LICENSE](LICENSE).
