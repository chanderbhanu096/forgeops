# ForgeOps — Complete Setup Guide

Everything you need to go from a fresh clone to a running ForgeOps instance.
Works on macOS, Linux and Windows (WSL2).

---

## Table of contents

1. [What you need](#1-what-you-need)
2. [Clone and configure](#2-clone-and-configure)
3. [Run locally with Docker](#3-run-locally-with-docker)
4. [Run the API without Docker](#4-run-the-api-without-docker-development)
5. [Run the tests](#5-run-the-tests)
6. [Submit your first mission](#6-submit-your-first-mission)
7. [Understanding the UI](#7-understanding-the-ui)
8. [Connect real tools (GitHub, data warehouse)](#8-connect-real-tools)
9. [Enable observability](#9-enable-observability)
10. [Deploy to AWS](#10-deploy-to-aws)
11. [Deploy to Azure](#11-deploy-to-azure)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. What you need

### To run locally

| Tool | Version | Why |
|---|---|---|
| Docker Desktop | 4.x+ | Runs the full stack in one command |
| An OpenAI API key | — | Powers the agent brain |
| Git | any | Clone the repo |

That is the **minimum**. Everything else is optional.

### To deploy to production

| Tool | Version | Why |
|---|---|---|
| Terraform | 1.7+ | Infrastructure as code |
| AWS CLI or Azure CLI | latest | Cloud authentication |
| A domain name | — | TLS certificate |

---

## 2. Clone and configure

```bash
# Clone
git clone https://github.com/chanderbhanu096/forgeops.git
cd forgeops

# Create your local config file
cp .env.example .env
```

Open `.env` in any editor and set at minimum:

```bash
OPENAI_API_KEY=sk-...        # required — get one at platform.openai.com
```

All other values have safe development defaults. You do not need to change anything else to get started.

**Full variable reference:**

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | **Yes** | — | gpt-4o, primary model |
| `ANTHROPIC_API_KEY` | No | empty | claude-3-5-sonnet, fallback if OpenAI fails |
| `POSTGRES_PASSWORD` | No | `forgeops_dev` | Local PostgreSQL password |
| `MCP_SECRET` | No | `forgeops_mcp_dev` | Auth token shared between API and MCP servers |
| `GITHUB_TOKEN` | No | empty | Needed for real PR creation. Get one at github.com/settings/tokens |
| `LANGFUSE_PUBLIC_KEY` | No | empty | LLM trace observability (langfuse.com) |
| `LANGFUSE_SECRET_KEY` | No | empty | LLM trace observability |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | No | empty | OTEL traces → Grafana Tempo, Jaeger etc. |
| `LOG_LEVEL` | No | `INFO` | `DEBUG` for verbose output |
| `ENVIRONMENT` | No | `development` | `staging` or `production` disables Swagger UI |

---

## 3. Run locally with Docker

This is the recommended way. One command starts everything.

```bash
docker compose up -d
```

This starts:
- **PostgreSQL 16** with pgvector extension (port 5432)
- **Redis 7** (port 6379)
- **API server** — FastAPI agent runtime (port 8000)
- **Mission Control UI** — Next.js 14 (port 3000)
- **GitHub MCP server** (port 8001)
- **Data Platform MCP server** (port 8002)
- **Knowledge MCP server** (port 8003)
- **Sandbox executor** — isolated code runner

**First run** builds all Docker images. Takes 3–5 minutes.
**Subsequent runs** start in ~15 seconds.

### Verify everything is up

```bash
docker compose ps
```

All services should show `healthy` or `running`.

```bash
curl http://localhost:8000/health
# → {"status": "ok"}
```

### Open the interfaces

| URL | What it is |
|---|---|
| http://localhost:3000 | Mission Control UI |
| http://localhost:8000/docs | Swagger API explorer |
| http://localhost:8000/metrics | Prometheus metrics |

### Stop everything

```bash
docker compose down          # stop containers, keep data
docker compose down -v       # stop containers AND delete all data
```

### View logs

```bash
docker compose logs -f api          # API server logs
docker compose logs -f web          # UI logs
docker compose logs -f mcp-github   # GitHub MCP logs
```

---

## 4. Run the API without Docker (development)

If you want to run the Python API directly for faster iteration:

### Prerequisites

```bash
# macOS
brew install python@3.11 postgresql redis

# Ubuntu / Debian
sudo apt install python3.11 python3.11-venv postgresql redis-server
```

### Install Python dependencies

```bash
cd apps/api

# Install Poetry (Python dependency manager)
curl -sSL https://install.python-poetry.org | python3 -

# Install all dependencies
poetry install

# Activate the virtual environment
poetry shell
```

### Start PostgreSQL and Redis

```bash
# macOS with Homebrew
brew services start postgresql@16
brew services start redis

# Or use Docker just for the infrastructure
docker compose up -d postgres redis
```

### Run database migrations

```bash
cd apps/api
alembic upgrade head
```

### Start the API

```bash
cd apps/api
uvicorn forgeops.app:app --reload --port 8000
```

The API is live at http://localhost:8000.

---

## 5. Run the tests

The test suite uses SQLite in-memory so **no Docker or database required**.

```bash
cd apps/api

# Run all 98 tests
PYTHONPATH=. pytest tests/ -v

# Run a specific module
PYTHONPATH=. pytest tests/test_agent_runtime.py -v
PYTHONPATH=. pytest tests/test_verification.py -v
PYTHONPATH=. pytest tests/test_multi_agent.py -v
PYTHONPATH=. pytest tests/test_memory.py -v
PYTHONPATH=. pytest tests/test_retrieval.py -v
PYTHONPATH=. pytest tests/test_missions_api.py -v
PYTHONPATH=. pytest tests/test_metrics.py -v

# Run the full demo integration scenario
PYTHONPATH=. pytest tests/demo/ -v

# Run with coverage report
PYTHONPATH=. pytest tests/ --cov=forgeops --cov-report=term-missing
```

Expected output: `98 passed in ~5s`.

---

## 6. Submit your first mission

### Via the Mission Control UI

1. Open http://localhost:3000
2. Click **New Mission**
3. Paste this example mission and click **Start**:

```
Investigate why the customer revenue pipeline is reporting 18% lower
revenue after yesterday's deployment. Find the root cause, identify
affected datasets, produce a safe fix and open a pull request.
```

4. Watch the **Execution Graph** update in real time as the agent works through each state.
5. When the agent reaches **HUMAN_APPROVAL**, the fix will appear in the **Approval Centre**.
6. Review the diff, evidence and test results — then click **Approve** or **Reject**.

### Via the REST API

```bash
# Create a mission
curl -X POST http://localhost:8000/api/v1/missions \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Revenue pipeline investigation",
    "description": "Revenue dashboard showing 18% lower figures after yesterdays release. Find and fix the root cause.",
    "max_steps": 50,
    "max_cost_usd": 2.0,
    "max_duration_seconds": 600
  }'

# Note the id from the response, then start it
curl -X POST http://localhost:8000/api/v1/missions/{id}/start

# Stream live progress
curl -N http://localhost:8000/api/v1/stream/{id}

# List pending approvals
curl http://localhost:8000/api/v1/approvals?decision=pending

# Approve a fix
curl -X POST http://localhost:8000/api/v1/approvals/{approval_id}/decide \
  -H "Content-Type: application/json" \
  -d '{"decision": "approved", "notes": "LGTM"}'
```

---

## 7. Understanding the UI

### Mission list (home page)

Shows all missions with status badges:
- **PENDING** — created, not started
- **RUNNING** — agent is actively working
- **AWAITING APPROVAL** — fix is ready, waiting for your decision
- **COMPLETED** — mission finished successfully
- **FAILED** — mission hit an unrecoverable error

### Mission detail page

**Execution Graph** (left panel) — shows the 13 states with live indicators:
- ✓ Completed state
- ◉ Current state (animated)
- ○ Future state

**Current Activity** (right panel) — live log of what the agent is doing right now.

**Budget Meters** — step count, cost (USD) and elapsed time. The agent stops automatically if any budget is exhausted.

**Diff Viewer** — appears when a code fix is generated. Shows exactly what files changed.

### Approval Centre

Every proposed fix must pass through here before the agent can create a PR or deploy anything.

You see:
- **Summary** — plain-English explanation of what the agent found and what it changed
- **Diff** — exact code changes in unified diff format
- **Evidence** — logs, SQL results and data that led to the diagnosis
- **Verifier results** — which automated checks passed and which flagged issues
- **Risk level** — low / medium / high / critical

You click **Approve** to proceed or **Reject** (with optional notes) to send the agent back to revise.

### Skills page

Lists all loaded skills with version, permissions and required tools. Skills are the agent's reusable capabilities — each one is a YAML file you can read, version and extend.

### Memory page

Shows the agent's accumulated knowledge across missions — episodic events, reusable facts, procedural strategies and feedback from past human decisions.

---

## 8. Connect real tools

### GitHub — enable real PR creation

1. Go to https://github.com/settings/tokens
2. Generate a **Classic** token with scopes: `repo`, `workflow`
3. Add to `.env`:
   ```bash
   GITHUB_TOKEN=ghp_...
   ```
4. Restart: `docker compose restart mcp-github api`

The agent will now create real branches and pull requests in repositories it has access to.

### Data warehouse — connect your own data

Edit `services/mcp-data/main.py`. The stub implementations at the top of the file are where you wire in your real data platform:

```python
# Replace these stubs with your actual connections:
# - Airflow REST API for pipeline runs
# - dbt Cloud API for model runs  
# - Snowflake / BigQuery / Redshift for SQL execution
# - DataHub / OpenMetadata / Atlan for lineage
# - Great Expectations / Soda for data quality
```

### Knowledge base — add your runbooks

Edit `services/mcp-knowledge/main.py`. Add your documentation sources:
- Confluence pages
- Notion databases
- Local markdown files
- PDF data contracts
- Incident history from PagerDuty / OpsGenie

---

## 9. Enable observability

### Langfuse — LLM trace explorer (free tier available)

1. Sign up at https://langfuse.com
2. Create a project → copy the public and secret keys
3. Add to `.env`:
   ```bash
   LANGFUSE_PUBLIC_KEY=pk-lf-...
   LANGFUSE_SECRET_KEY=sk-lf-...
   ```
4. Every model call (prompt, completion, cost, latency) will appear in your Langfuse dashboard.

### OpenTelemetry — distributed traces (Grafana Tempo / Jaeger)

```bash
# Start Grafana Tempo locally
docker run -d --name tempo -p 4318:4318 grafana/tempo:latest

# Add to .env
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
```

State transitions, tool calls and verifier runs will appear as spans.

### Prometheus + Grafana — metrics dashboard

```bash
# Add to docker-compose.yml or run separately
docker run -d --name prometheus -p 9090:9090 \
  -v ./infra/docker/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus

docker run -d --name grafana -p 3001:3000 grafana/grafana
```

Point Prometheus at `http://host.docker.internal:8000/metrics`.

Available metrics:
- `forgeops_missions_total{status}` — missions by status
- `forgeops_model_cost_usd_total` — cumulative LLM spend
- `forgeops_tool_calls_total{server,tool}` — MCP tool invocations
- `forgeops_verifier_runs_total{pipeline,passed}` — verification results
- `forgeops_approvals_pending` — approvals waiting for decision

---

## 10. Deploy to AWS

Full instructions in [DEPLOYMENT.md](DEPLOYMENT.md). Quick summary:

### Prerequisites

- Terraform 1.7+
- AWS CLI: `aws configure` with a deployment role
- An ACM certificate for your domain
- Docker

### Steps

```bash
cd infra/aws

# Create your variables file (never commit this)
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

# Deploy infrastructure (~8 minutes)
terraform init
terraform plan
terraform apply

# Push Docker images
ECR=$(terraform output -raw ecr_repository_urls)
aws ecr get-login-password --region eu-west-1 | \
  docker login --username AWS --password-stdin $ECR

for svc in api web mcp-github mcp-data mcp-knowledge; do
  docker build -t $ECR/forgeops-$svc:latest apps/$svc/
  docker push $ECR/forgeops-$svc:latest
done

# Force redeployment
aws ecs update-service \
  --cluster forgeops-staging-cluster \
  --service forgeops-staging-api \
  --force-new-deployment
```

What gets created:
- VPC with public/private subnets
- ECS Fargate cluster (API, web, 3 MCP servers)
- RDS PostgreSQL 16
- ElastiCache Redis 7
- Application Load Balancer with TLS
- ECR repositories
- CloudWatch log groups
- IAM roles with least-privilege policies

### CI/CD via GitHub Actions

Set these repository secrets (Settings → Secrets → Actions):
```
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
OPENAI_API_KEY
```

Set these repository variables:
```
DEPLOY_TARGET        = aws
AWS_REGION           = eu-west-1
ECS_CLUSTER          = forgeops-staging-cluster
DEPLOY_ENVIRONMENT   = staging
```

Every push to `main` runs: **test → build → push → deploy**.

---

## 11. Deploy to Azure

```bash
cd infra/azure

cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

az login
terraform init
terraform plan
terraform apply
```

What gets created:
- Azure Container Apps environment
- PostgreSQL Flexible Server 16
- Azure Cache for Redis
- Azure Container Registry
- Key Vault for secrets
- Managed Identity for authentication

### CI/CD via GitHub Actions

```bash
# Create service principal and copy the JSON output
az ad sp create-for-rbac --sdk-auth
```

Set repository secret:
```
AZURE_CREDENTIALS   = (JSON from the command above)
OPENAI_API_KEY      = sk-...
```

Set repository variables:
```
DEPLOY_TARGET        = azure
ACR_NAME             = forgeopsstagingacr
ACR_LOGIN_SERVER     = forgeopsstagingacr.azurecr.io
DEPLOY_ENVIRONMENT   = staging
```

---

## 12. Troubleshooting

### "Connection refused" on port 8000

The API container is still starting. PostgreSQL must be healthy first.

```bash
docker compose logs postgres   # check for "ready to accept connections"
docker compose logs api        # check for "forgeops_starting"
```

### "OPENAI_API_KEY not set" error

Make sure your `.env` file exists and contains the key:

```bash
cat .env | grep OPENAI
```

If empty, add the key and restart:

```bash
docker compose restart api
```

### Database migration errors

```bash
# Reset the database completely
docker compose down -v
docker compose up -d postgres
sleep 5
docker compose up -d api   # migrations run automatically on startup
```

### Tests failing with "no module named forgeops"

Always run tests with `PYTHONPATH=.` from the `apps/api` directory:

```bash
cd apps/api
PYTHONPATH=. pytest tests/ -v
```

### Port already in use

```bash
# Check what's using the port
lsof -i :8000
lsof -i :3000
lsof -i :5432

# Kill it or change the port in docker-compose.yml
```

### MCP server authentication errors

The API and MCP servers share a `MCP_SECRET`. Make sure it matches in `.env`:

```bash
grep MCP_SECRET .env
# Should be the same value for all MCP services
```

### Terraform apply fails with "provider not found"

```bash
cd infra/aws   # or infra/azure
terraform init  # downloads provider plugins
terraform apply
```

---

## Getting help

- **Issues**: https://github.com/chanderbhanu096/forgeops/issues
- **Docs**: [`docs/architecture.md`](docs/architecture.md) — deep-dive into every system
- **API reference**: [`docs/api.md`](docs/api.md) — all endpoints documented
- **Skills**: [`docs/skills.md`](docs/skills.md) — how to add your own skills
- **Contributing**: [`CONTRIBUTING.md`](CONTRIBUTING.md) — dev conventions and PR process
