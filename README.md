<div align="center">

# ⚙️ ForgeOps AI

### An approval-controlled AI engineer for software, data and cloud incidents

**Investigate → collect evidence → identify root cause → verify a fix → request human approval**

[![CI / CD](https://github.com/chanderbhanu096/forgeops/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/chanderbhanu096/forgeops/actions/workflows/ci-cd.yml)
[![Quality Gates](https://github.com/chanderbhanu096/forgeops/actions/workflows/quality-gates.yml/badge.svg)](https://github.com/chanderbhanu096/forgeops/actions/workflows/quality-gates.yml)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000?logo=nextdotjs&logoColor=white)](https://nextjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://postgresql.org)

[**Open the live demo**](https://forgeops-staging-web.greenrock-70958585.northeurope.azurecontainerapps.io) · [Start locally](#start-in-60-seconds) · [Add an LLM](#add-an-llm-provider) · [Architecture](#architecture)

</div>

---

## What makes ForgeOps trustworthy

ForgeOps is designed to stop rather than invent an answer. Repository-review missions must identify a concrete GitHub repository and retrieve cited source evidence before the system can create hypotheses, propose a patch, or claim that verification or monitoring succeeded.

When repository access or evidence retrieval fails, the mission ends with a clear error and preserves its checkpoint for inspection.

## Production quality gates

Pull requests run all of the following automatically:

- Ruff linting for production Python code
- Full pytest suite with coverage
- Next.js ESLint checks
- TypeScript type checking
- Next.js production build
- Docker Compose validation
- Deterministic image builds for every Compose service

Run the same checks locally:

```bash
cd apps/api
poetry install --with dev
poetry run ruff check forgeops
poetry run pytest tests/ -v

cd ../web
npm ci
npm run lint
npm run type-check
npm run build

cd ../..
docker compose config --quiet
docker compose build --pull
```

## Start in 60 seconds

```bash
git clone https://github.com/chanderbhanu096/forgeops.git
cd forgeops
cp .env.example .env
docker compose up --build
```

Open `http://localhost:3000`.

The built-in demo provider works without an external model key. Configure one of the supported providers in `.env` for live model execution.

## Test a repository review

```text
Review the repository at https://github.com/OWNER/REPOSITORY.
Analyze the main branch in read-only mode.
Show the repository URL, branch or commit, files inspected, and evidence for
all confirmed findings. Keep assumptions separate. Do not generate a patch or
claim tests passed unless source evidence and actual test output are available.
Stop for human review before any change.
```

## GitHub App access

Use a GitHub App with read-only repository permissions by default. Store credentials only in GitHub Actions or Azure secrets.

```text
FORGEOPS_GITHUB_APP_ID
FORGEOPS_GITHUB_APP_PRIVATE_KEY
FORGEOPS_GITHUB_INSTALLATION_ID
MCP_SECRET
```

Never commit private keys or long-lived tokens. Write operations should require explicit approval of the exact repository, branch, patch, and pull-request scope.

## Architecture

```text
Next.js Mission Control
        │
        ▼
FastAPI mission API ── PostgreSQL checkpoints
        │
        ├── Model providers
        ├── Retrieval and evidence pipeline
        ├── Deterministic verification
        ├── GitHub MCP
        └── Human approval gate
```

## Add an LLM provider

ForgeOps supports server-side provider configuration through environment variables. The UI never receives secret values.

Common options include Groq, OpenAI, Anthropic, OpenRouter, Ollama, and custom OpenAI-compatible endpoints. Set the provider key and model list in `.env`, restart the API, and select the provider while creating a mission.

## Safety model

- Read-only investigation by default
- Evidence required before findings
- Deterministic checks before approval
- Human approval before execution
- Durable checkpoints for auditability
- Secrets kept on the server

## License

See the repository license for usage terms.
