<div align="center">

# ⚙️ ForgeOps AI

### An approval-controlled AI engineer for data, cloud and software operations

**Give it a mission → watch the investigation → review the evidence → approve before execution.**

[![CI / CD](https://github.com/chanderbhanu096/forgeops/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/chanderbhanu096/forgeops/actions/workflows/ci-cd.yml)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000?logo=nextdotjs&logoColor=white)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)

[**Open the live app**](https://forgeops-staging-web.greenrock-70958585.northeurope.azurecontainerapps.io) · [60-second start](#60-second-start) · [Add an LLM](#add-an-llm-provider) · [Architecture](#architecture)

</div>

---

## See it working before installing anything

The screenshots below are captured automatically from the deployed application after a successful release. They are not design mockups.

### 1. Mission Control

![Live ForgeOps Mission Control](docs/images/live/01-mission-control.png)

### 2. Create a mission and choose an AI model

![Live ForgeOps create mission form](docs/images/live/02-create-mission.png)

### 3. Watch the state machine work

![Live ForgeOps execution progress](docs/images/live/03-execution-progress.png)

### 4. Read the actual analysis result

![Live ForgeOps AI analysis report](docs/images/live/04-analysis-report.png)

> The screenshots are refreshed by `.github/workflows/capture-live-demo.yml` after deployment.

---

## What ForgeOps actually does

ForgeOps is not a chat screen. It is a durable engineering-agent workflow that:

1. Understands the environment.
2. Builds an investigation plan.
3. Collects and ranks evidence.
4. Creates and verifies root-cause hypotheses.
5. Generates a proposed fix.
6. Runs deterministic and model-based review.
7. Shows a human-readable analysis report.
8. Stops for human approval before execution.
9. Records state, cost, model, evidence and audit history in PostgreSQL.

The mission result page shows the environment, plan, evidence, hypotheses, confidence, verification findings, changed files and generated patch—not only a progress bar.

---

# 60-second start

You only need **Git** and **Docker Desktop**.

## 1. Download ForgeOps

```bash
git clone https://github.com/chanderbhanu096/forgeops.git
cd forgeops
```

## 2. Create your private settings file

macOS/Linux:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

## 3. Start everything

```bash
docker compose up --build
```

The first build takes longer because Docker downloads and builds the services. Later starts are much faster.

## 4. Open the app

Open **http://localhost:3000**.

Click **Run the guided demo**. No API key is required. ForgeOps fills the mission form, uses the demo model and opens the live result page automatically.

### Useful local addresses

| Address | Purpose |
|---|---|
| http://localhost:3000 | ForgeOps UI |
| http://localhost:8000/docs | Interactive API docs |
| http://localhost:8000/health | API health check |
| http://localhost:8000/metrics | Prometheus metrics |

## Stop the app

```bash
docker compose down
```

Remove all local data and start fresh:

```bash
docker compose down -v
```

---

# Add an LLM provider

ForgeOps always includes the free **Demo simulator**. To use a real model, add one provider to `.env`, restart Docker and select it in the UI.

## Groq — easiest hosted option

Add these lines to `.env`:

```dotenv
GROQ_API_KEY=gsk_your_real_key_here
DEFAULT_LLM_PROVIDER=groq
DEFAULT_LLM_MODEL=openai/gpt-oss-20b
```

Restart only the API and web containers:

```bash
docker compose up -d --build api web
```

## OpenAI

```dotenv
OPENAI_API_KEY=your_key_here
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=gpt-5-mini
```

## Anthropic / Claude

```dotenv
ANTHROPIC_API_KEY=your_key_here
DEFAULT_LLM_PROVIDER=anthropic
DEFAULT_LLM_MODEL=claude-sonnet-4-20250514
```

## OpenRouter

```dotenv
OPENROUTER_API_KEY=your_key_here
DEFAULT_LLM_PROVIDER=openrouter
DEFAULT_LLM_MODEL=openrouter/auto
```

## Ollama — local model, no hosted API key

Start Ollama separately, then add:

```dotenv
OLLAMA_BASE_URL=http://host.docker.internal:11434
DEFAULT_LLM_PROVIDER=ollama
DEFAULT_LLM_MODEL=llama3.2
```

## Any OpenAI-compatible provider

```dotenv
CUSTOM_OPENAI_NAME=My provider
CUSTOM_OPENAI_BASE_URL=https://provider.example.com/v1
CUSTOM_OPENAI_API_KEY=your_key_here
DEFAULT_LLM_PROVIDER=custom
DEFAULT_LLM_MODEL=provider-model-id
```

Restart:

```bash
docker compose up -d --build api web
```

Confirm that ForgeOps detected the provider:

```bash
curl http://localhost:3000/api/backend/api/v1/models
```

Look for:

```json
"configured": true
```

The UI marks configured providers with `✓`. Unconfigured providers remain visible but disabled, with an explanation of which setting is missing.

More details: [docs/MODEL_PROVIDERS.md](docs/MODEL_PROVIDERS.md)

> Never commit `.env` or paste API keys into source code, README files, screenshots or logs.

---

# Try this mission

**Title**

```text
Analyze a simulated API deployment failure
```

**Description**

```text
Treat this as a simulated, non-destructive incident. Do not access production
systems or make external changes.

Known facts:
- The frontend and API health endpoint are reachable.
- A mission can still fail after the health check passes.
- The application uses FastAPI, Next.js, PostgreSQL, GitHub Actions and Azure
  Container Apps.

Produce a visible investigation report containing the environment, investigation
plan, evidence, three hypotheses, the most likely root cause, a safe remediation,
regression tests, risks and a confidence score. Stop before destructive action.
```

For a quick UI demonstration, choose **Demo simulator**. For real model-generated analysis, choose a configured hosted or local provider.

---

# Approval workflow

Real-provider missions pause at **Human Approval**.

1. Open the mission result.
2. Read the analysis report and proposed patch.
3. Open **Approval Centre**.
4. Review the summary, risk and diff.
5. Click **Approve** to continue or **Reject** to stop.

ForgeOps persists the decision and resumes from the approval gate only after approval.

---

# Why it may feel slow

A real mission makes several sequential model calls for environment discovery, planning, evidence, hypotheses, solution generation, review and monitoring. That is intentional: each stage is persisted and auditable.

Performance improvements included in this repository:

- Home-page API requests run in parallel.
- Mission creation navigates directly to the result page.
- Large code patches are collapsed until requested.
- Completed mission pages stop re-rendering every second.
- Azure API and web containers keep one warm replica in the provided deployment workflow.
- Docker and GitHub Actions use build caches.

The Demo simulator is the fastest way to review the interface. Real-model duration depends on provider latency and model size.

---

# Troubleshooting

## The website is slow on the first request

A cloud container may still be starting or a new revision may be warming up. Wait a few seconds and refresh once. The Azure workflow keeps one replica warm after deployment, but revision changes can still cause a short warm-up.

## “Failed to fetch”

```bash
curl http://localhost:8000/health
docker compose logs --tail=100 api web
```

Then restart:

```bash
docker compose restart api web
```

## Provider says “not configured”

- Put the key in `.env`, not `.env.example`.
- Use the exact variable name.
- Restart `api` and `web` after changing `.env`.
- Check `/api/v1/models` with the command above.

## Mission waits for approval

That is expected for a real provider. Open **Approval Centre**.

## Start completely fresh

```bash
docker compose down -v
docker compose up --build
```

---

# What recruiters can evaluate quickly

| Area | Evidence |
|---|---|
| AI engineering | Multi-provider model gateway and per-mission routing |
| Agent systems | Durable state machine, budgets, checkpoints and pause/resume |
| RAG | Query decomposition, retrieval, reranking, compression and citations |
| Safety | Deterministic verification, sandboxing and human approval |
| Backend | Async FastAPI, SQLAlchemy, PostgreSQL and SSE |
| Frontend | Next.js mission control, live progress and analysis report |
| Platform | Docker, GitHub Actions, ACR and Azure Container Apps |
| Testing | Runtime, API, retrieval, memory, verifier and approval tests |
| Observability | Structured logs, Prometheus and OpenTelemetry |

---

# Architecture

```text
Mission Control UI
        │ REST + SSE
        ▼
FastAPI mission API
        │
        ▼
Durable agent state machine
        ├── Model gateway: OpenAI / Claude / Groq / OpenRouter / Ollama / custom
        ├── Retrieval and memory
        ├── Deterministic verification
        ├── Multi-agent review
        └── Human approval gate
        │
        ▼
PostgreSQL + Redis + tool services + observability
```

## State flow

```text
MISSION RECEIVED
→ ENVIRONMENT DISCOVERY
→ PLAN GENERATION
→ EVIDENCE COLLECTION
→ HYPOTHESIS CREATION
→ HYPOTHESIS VERIFICATION
→ SOLUTION GENERATION
→ SANDBOX EXECUTION
→ TEST AND REVIEW
→ HUMAN APPROVAL
→ EXECUTION
→ POST-ACTION MONITORING
→ COMPLETED
```

---

# Project structure

```text
apps/api/                 FastAPI runtime, models, routes and tests
apps/web/                 Next.js Mission Control
services/                 Sandbox and MCP-style tool services
infra/azure/              Azure infrastructure
infra/aws/                AWS infrastructure
docs/                     Architecture and provider documentation
scripts/                  Live demo and screenshot automation
.github/workflows/        CI/CD and screenshot capture
```

---

# Tests

```bash
docker compose run --rm api poetry run pytest tests/ -v
```

CI runs linting and the complete backend suite before images are built or deployed.

---

# Security and scope

- Provider credentials stay server-side.
- Demo mode does not access external systems.
- Real connectors should use least-privilege credentials.
- Generated changes pass verification and human approval gates.
- ForgeOps is a portfolio-grade reference implementation. Production adoption would additionally require organization-specific authentication, authorization, evaluation datasets, hardened connectors and compliance controls.

---

## License

[MIT](LICENSE)
