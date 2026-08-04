<div align="center">

# ⚙️ ForgeOps AI

### An approval-controlled AI engineer for data, cloud and software operations

**Give it a mission. Watch it investigate. Review the evidence. Approve before execution.**

[![CI / CD](https://github.com/chanderbhanu096/forgeops/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/chanderbhanu096/forgeops/actions/workflows/ci-cd.yml)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000?logo=nextdotjs&logoColor=white)](https://nextjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://postgresql.org)
[![License](https://img.shields.io/badge/license-MIT-6366f1)](LICENSE)

[**Open the live application**](https://forgeops-staging-web.greenrock-70958585.northeurope.azurecontainerapps.io) · [Beginner setup](#run-it-locally-beginner-guide) · [Architecture](#architecture) · [Model providers](docs/MODEL_PROVIDERS.md)

</div>

---

## See the product before installing anything

The hosted application lets a recruiter, engineer or reviewer understand the project without setting up Python, Docker or a database.

[**Launch ForgeOps Mission Control →**](https://forgeops-staging-web.greenrock-70958585.northeurope.azurecontainerapps.io)

> The images below are illustrated previews based on the current interface. The live application shows the working product.

### 1. Create a mission and choose the model

![ForgeOps Mission Control](docs/images/mission-control-preview.svg)

### 2. Follow the durable execution graph

![ForgeOps execution graph](docs/images/execution-preview.svg)

### 3. Review the evidence and approve or reject

![ForgeOps Approval Centre](docs/images/approval-centre-preview.svg)

---

## What is ForgeOps?

ForgeOps turns an engineering goal into a controlled, auditable workflow.

Example mission:

```text
Investigate why the API deployment is failing, identify the root cause,
verify a safe fix and prepare the result for human approval.
```

ForgeOps moves through a persistent state machine:

```text
MISSION RECEIVED
      ↓
ENVIRONMENT DISCOVERY
      ↓
PLAN GENERATION
      ↓
EVIDENCE COLLECTION
      ↓
HYPOTHESIS CREATION + VERIFICATION
      ↓
SOLUTION GENERATION
      ↓
SANDBOX TESTING + REVIEW
      ↓
HUMAN APPROVAL
      ↓
EXECUTION + POST-ACTION MONITORING
```

Every mission stores its state, model, cost, step count, evidence and transitions in PostgreSQL. If the process stops, the mission can be inspected and resumed instead of losing its progress.

### Why it is not just another chatbot

A normal chatbot mainly returns text. ForgeOps demonstrates the engineering systems required around an AI worker:

- A durable state machine rather than a single prompt-response call
- Step, time and cost budgets
- Per-mission model selection
- Deterministic verification before approval
- Human-in-the-loop execution controls
- Persistent memory and audit history
- MCP-style tool services
- CI/CD deployment to Azure Container Apps
- Live progress through REST and server-sent events

---

## What works without external credentials?

ForgeOps includes a **Demo simulator**. It runs the full visible state-machine flow without calling a paid model or accessing external systems.

This is useful for:

- Exploring the interface
- Demonstrating the approval-controlled workflow
- Running tests
- Understanding the architecture
- Reviewing the project during an interview

For real model-generated analysis, configure one provider such as Groq, OpenAI, Anthropic or OpenRouter.

> External repositories, data platforms and production systems require their own credentials and connector configuration. ForgeOps never receives that access automatically.

---

# Run it locally: beginner guide

You do not need to install Python, PostgreSQL, Redis or Node.js separately. Docker starts everything for you.

## What you need

1. [Git](https://git-scm.com/downloads)
2. [Docker Desktop](https://www.docker.com/products/docker-desktop/)
3. Around 6 GB of free memory for the complete local stack

Open Docker Desktop and wait until it says Docker is running.

## Step 1 — Download the project

Open Terminal on macOS/Linux or PowerShell on Windows:

```bash
git clone https://github.com/chanderbhanu096/forgeops.git
cd forgeops
```

## Step 2 — Create your private settings file

### macOS or Linux

```bash
cp .env.example .env
```

### Windows PowerShell

```powershell
Copy-Item .env.example .env
```

The `.env` file contains local settings and API keys. It is ignored by Git and must never be committed.

## Step 3 — Start in free demo mode

The example configuration already defaults to:

```dotenv
DEFAULT_LLM_PROVIDER=demo
DEFAULT_LLM_MODEL=forgeops-demo
```

Start the full stack:

```bash
docker compose up --build
```

The first build may take several minutes. Wait until the services stop printing startup errors.

## Step 4 — Open ForgeOps

| Address | Purpose |
|---|---|
| http://localhost:3000 | Mission Control web application |
| http://localhost:8000/docs | Interactive API documentation |
| http://localhost:8000/health | API health check |
| http://localhost:8000/metrics | Prometheus-compatible metrics |

Open **http://localhost:3000** and create a mission using the **Demo simulator** provider.

## Step 5 — Try this first mission

**Title**

```text
Analyze a simulated API deployment failure
```

**Description**

```text
Treat this as a simulated incident. Do not access external systems and do not
make destructive changes.

Known facts:
- The health endpoint works.
- Mission execution previously failed because a step counter was incremented twice.
- The defect has been fixed.

Explain the likely root cause, provide a verification plan and recommend three
regression tests. Pause before any execution that would change a system.
```

The mission should move through the execution graph and finish automatically in demo mode.

## Stop ForgeOps

Press `Ctrl + C` in the terminal, then run:

```bash
docker compose down
```

Your PostgreSQL and Redis data remain in Docker volumes.

To remove all local ForgeOps data and start completely fresh:

```bash
docker compose down -v
```

---

# Use a real AI model

Only configure the provider you plan to use. Keep all API keys inside `.env` locally or a cloud secret manager in production.

## Easiest option: Groq

Open `.env` and change these lines:

```dotenv
GROQ_API_KEY=gsk_your_real_key_here
DEFAULT_LLM_PROVIDER=groq
DEFAULT_LLM_MODEL=openai/gpt-oss-20b
```

Restart:

```bash
docker compose down
docker compose up --build
```

Open Mission Control. **Groq** should now be selectable.

## Other supported providers

| Provider | Secret or setting | Example model |
|---|---|---|
| Demo simulator | Nothing required | `forgeops-demo` |
| OpenAI | `OPENAI_API_KEY` | `gpt-5-mini` |
| Anthropic / Claude | `ANTHROPIC_API_KEY` | `claude-sonnet-4-20250514` |
| Groq | `GROQ_API_KEY` | `openai/gpt-oss-20b` |
| OpenRouter | `OPENROUTER_API_KEY` | `openrouter/auto` |
| Ollama | `OLLAMA_BASE_URL` | `llama3.2` |
| Other OpenAI-compatible service | `CUSTOM_OPENAI_BASE_URL` | Provider-specific |

Provider model catalogs change. The model field in ForgeOps is editable, so you can enter a model ID supported by your configured provider.

Detailed configuration: **[docs/MODEL_PROVIDERS.md](docs/MODEL_PROVIDERS.md)**

## Confirm that the provider is available

```bash
curl http://localhost:3000/api/backend/api/v1/models
```

Find your provider and check that it contains:

```json
"configured": true
```

---

# How to use the approval workflow

Real-provider missions pause at **Human Approval**.

1. Open the mission details page.
2. Click **Go to Approval Centre**.
3. Review the summary, risk level and generated diff.
4. Add an optional review note.
5. Click **Approve** to continue or **Reject** to stop the mission.

Approval decisions are persisted in PostgreSQL as part of the audit trail. ForgeOps resumes from the approval gate and runs the execution handler only after approval.

---

# Troubleshooting for beginners

## The website does not open

Check the running containers:

```bash
docker compose ps
```

Read the most recent logs:

```bash
docker compose logs --tail=100
```

## The UI says “Failed to fetch”

Confirm the API is healthy:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status":"ok"}
```

Then restart the web and API services:

```bash
docker compose restart api web
```

## My provider appears as “not configured”

1. Confirm the key is in `.env`, not `.env.example`.
2. Confirm the variable name is exact, for example `GROQ_API_KEY`.
3. Restart the containers after editing `.env`.
4. Run the model-catalog check shown above.

## A mission waits for approval

That is expected for a real provider. Open **Approval Centre** from the navigation or the mission detail page.

## A port is already being used

ForgeOps uses ports `3000`, `5432`, `6379`, `8000`, `8001`, `8002` and `8003`. Stop the program using the conflicting port or change the mapping in `docker-compose.yml`.

## Start completely fresh

```bash
docker compose down -v
docker compose up --build
```

---

# What a recruiter can evaluate in two minutes

| Area | Evidence in this repository |
|---|---|
| AI engineering | Multi-provider gateway, structured tool calls, context management and per-mission routing |
| Agent systems | Durable 13-state runtime with checkpoints, budgets, pause/resume and approval gates |
| RAG and retrieval | Query routing, BM25 retrieval, reranking, compression and evidence handling |
| Safety | Deterministic verifiers, sandboxing, risk classification and explicit approval |
| Backend engineering | Async FastAPI, SQLAlchemy, PostgreSQL, migrations and SSE |
| Frontend engineering | Next.js Mission Control interface with live execution progress |
| Platform engineering | Docker Compose, GitHub Actions, Azure Container Apps and container registry |
| Testing | Automated runtime, API, retrieval, memory, verifier and approval-workflow tests |
| Observability | Structured logs, Prometheus metrics, OpenTelemetry and optional Langfuse |

---

# Architecture

```text
┌────────────────────────────────────────────────────────────┐
│                   Mission Control UI                       │
│       New mission · execution graph · diff · approval      │
└───────────────────────────┬────────────────────────────────┘
                            │ REST + SSE
┌───────────────────────────▼────────────────────────────────┐
│                      FastAPI API                           │
│       Missions · approvals · skills · memory · metrics     │
└───────────────────────────┬────────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────────┐
│               Durable Agent State Machine                  │
│  checkpoints · budgets · handlers · pause/resume · audit   │
└───────────────┬──────────────────────────────┬─────────────┘
                │                              │
┌───────────────▼──────────────┐  ┌────────────▼─────────────┐
│       Model Gateway          │  │     Skill + Tool Layer    │
│ OpenAI · Claude · Groq       │  │ GitHub · data · knowledge │
│ OpenRouter · Ollama · custom │  │ MCP services · sandbox    │
└──────────────────────────────┘  └──────────────────────────┘
                │                              │
┌───────────────▼──────────────────────────────▼─────────────┐
│ PostgreSQL + pgvector · Redis · verification · observability│
└────────────────────────────────────────────────────────────┘
```

## Core engineering systems

### Durable runtime

Every successful transition is written to the database. Missions enforce maximum steps, cost and duration. State is recoverable after a restart.

### Model gateway

The model provider and model are stored per mission. Concurrent missions can use different providers without sharing selection state. API keys remain server-side and are never returned to the browser.

### Verification-first design

Generated code, SQL and infrastructure changes pass deterministic verifier chains. Checks include syntax, dangerous patterns, imports, patch size, SQL safety and Terraform security rules.

### Multi-agent review

A builder, reviewer, security agent, deterministic verifier and judge perform separate roles before the human approval gate.

### Retrieval and memory

ForgeOps contains source routing, sparse retrieval, reranking, context compression and persistent episodic, semantic, procedural and feedback memory.

### MCP-style tool services

The repository includes GitHub, data-platform and knowledge services. They demonstrate the tool boundary and can be connected to real systems with appropriate credentials and implementation-specific configuration.

---

# Project structure

```text
forgeops/
├── apps/
│   ├── api/                         FastAPI agent runtime
│   │   ├── forgeops/agent/          State machine, handlers and model gateway
│   │   ├── forgeops/api/routes/     Mission, approval, memory and metrics APIs
│   │   ├── forgeops/verification/   Code, SQL and infrastructure verifiers
│   │   ├── forgeops/retrieval/      Retrieval and reranking pipeline
│   │   ├── forgeops/memory/         Persistent operational memory
│   │   └── tests/                   Automated backend tests
│   └── web/                         Next.js Mission Control UI
├── services/                        Sandbox and MCP-style tool services
├── infra/aws/                       AWS Terraform modules
├── infra/azure/                     Azure Terraform modules
├── docs/                            Setup and provider documentation
├── docker-compose.yml               Complete local stack
└── .github/workflows/ci-cd.yml      Test, build and cloud deployment
```

---

# Running the automated tests

The easiest option is to run them inside the API container:

```bash
docker compose run --rm api poetry run pytest tests/ -v
```

For local Python development:

```bash
cd apps/api
pip install poetry==1.8.3
poetry install --with dev
poetry run ruff check forgeops/
poetry run pytest tests/ -v
```

The CI pipeline runs linting and the backend test suite before building or deploying images.

---

# Deploying

The repository includes a GitHub Actions workflow for container builds and deployment to Azure Container Apps or AWS ECS.

For the Azure deployment used by the live application:

1. Add cloud credentials under **GitHub → Settings → Secrets and variables → Actions**.
2. Add model API keys as GitHub Actions secrets.
3. Add non-sensitive deployment settings as repository variables.
4. Push to `main`.
5. CI tests the code, builds images, pushes them to the registry and updates the cloud applications.

See [SETUP.md](SETUP.md) and [docs/MODEL_PROVIDERS.md](docs/MODEL_PROVIDERS.md) for detailed configuration.

---

# Security notes

- Never commit `.env` or API keys.
- Provider credentials remain on the API server.
- The frontend receives only provider availability and model suggestions.
- Approval records contain the decision and reviewer notes, not provider credentials.
- Demo mode does not access external systems.
- Real external-system access should use least-privilege credentials and isolated environments.

---

# Current scope

ForgeOps is a portfolio-grade engineering platform and reference implementation. It demonstrates the architecture, runtime, UI, provider routing, verification, approval controls, tests and cloud deployment expected in a serious agentic system.

Production use would additionally require organization-specific authentication, authorization, secret management, connector hardening, evaluation datasets, operational runbooks and compliance review.

---

## License

[MIT](LICENSE)
