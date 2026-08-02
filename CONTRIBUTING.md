# Contributing to ForgeOps

Thank you for your interest. This document covers everything you need to get started.

---

## Development setup

```bash
git clone https://github.com/your-org/forgeops.git
cd forgeops

# Python API
cd apps/api
pip install poetry
poetry install
cp ../../.env.example ../../.env   # set OPENAI_API_KEY

# Run tests (no Docker needed for tests — uses SQLite in-memory)
PYTHONPATH=. pytest tests/ -v

# Start the full stack
cd ../..
docker compose up -d
```

---

## Project conventions

### Python

- **Formatter / linter**: Ruff (`ruff check .` and `ruff format .`)
- **Type checker**: MyPy (`mypy forgeops/`)
- **Style**: all public functions must have type annotations; `from __future__ import annotations` at the top of every file
- **Async**: all I/O is async; synchronous blocking calls go through `run_in_executor`
- **Imports**: absolute (`from forgeops.agent.gateway import ModelGateway`), not relative

### TypeScript / Next.js

- **Formatter**: Prettier (`.prettierrc` in `apps/web/`)
- **Linter**: ESLint (`next lint`)
- **Style**: `interface` for object shapes, `type` for unions/primitives

### Terraform

- All variable blocks with more than one argument must use multi-line syntax — single-line `{ type = T default = V }` is not valid HCL
- Every module must have at least one `output` block

---

## Adding a new skill

1. Create `apps/api/forgeops/skills/definitions/<name>.yaml` following the schema in any existing skill file.
2. Declare `required_tools`, `permissions`, `inputs` and `outputs`.
3. Bump the version using semver (`1.0.0` for new skills).
4. Add a test in `tests/test_skill_registry.py` that loads the skill and asserts on key fields.

---

## Adding a new verifier

1. Create a class in the appropriate verifier module (`code_verifiers.py`, `sql_verifiers.py`, `infra_verifiers.py`).
2. Implement `verify(self, **payload) -> VerifierResult`.
3. Add it to the appropriate chain in `pipeline.py`.
4. Add tests in `tests/test_verification.py`.

Verifiers must be:
- **Deterministic** — same input always returns same result
- **Read-only** — never modify the payload
- **Independent** — no shared mutable state with other verifiers

---

## Adding a new MCP tool

1. Add the handler function to the relevant MCP server in `services/mcp-*/main.py`.
2. Register it in the tool manifest at the top of that file.
3. Update the skill YAML(s) that should have access to it.
4. Document the inputs/outputs in `docs/api.md`.

---

## Pull request process

1. Open an issue describing the change before starting large work.
2. Branch from `main`: `git checkout -b feat/your-feature`.
3. Keep commits small and focused — one logical change per commit.
4. Tests must pass: `PYTHONPATH=. pytest tests/ -v`
5. No new Ruff warnings: `ruff check apps/api/forgeops/`
6. Update `DEPLOYMENT.md` if you change any environment variables or infrastructure.
7. Open a PR against `main`. The CI pipeline runs automatically.

---

## Commit message format

```
type(scope): short description

Optional longer body explaining the why.
```

Types: `feat` · `fix` · `refactor` · `test` · `docs` · `chore` · `infra`

Examples:
```
feat(agent): add rollback handler to post_action_monitoring state
fix(verification): use Severity enum constants instead of bare strings
docs(readme): add architecture overview and quick start
infra(aws): fix multi-argument variable blocks in ecs-service module
```

---

## Where to find things

| What you want to change | Where it lives |
|---|---|
| Agent state machine transitions | `apps/api/forgeops/agent/runtime.py` — `TRANSITIONS` dict |
| State handler logic | `apps/api/forgeops/agent/handlers.py` — `handle_<state>` functions |
| LLM provider / fallback | `apps/api/forgeops/agent/gateway.py` |
| Multi-agent review pipeline | `apps/api/forgeops/agent/multi_agent.py` |
| Skill definitions | `apps/api/forgeops/skills/definitions/*.yaml` |
| Code/SQL/Terraform verifiers | `apps/api/forgeops/verification/` |
| Memory store | `apps/api/forgeops/memory/store.py` |
| Retrieval orchestrator | `apps/api/forgeops/retrieval/orchestrator.py` |
| ORM models | `apps/api/forgeops/models/orm.py` |
| API routes | `apps/api/forgeops/api/routes/` |
| Mission Control UI | `apps/web/src/` |
| GitHub MCP server | `services/mcp-github/main.py` |
| Data platform MCP | `services/mcp-data/main.py` |
| Knowledge MCP | `services/mcp-knowledge/main.py` |
| AWS Terraform | `infra/aws/` |
| Azure Terraform | `infra/azure/` |
| CI/CD pipeline | `.github/workflows/ci-cd.yml` |

---

## Running specific test modules

```bash
cd apps/api

# Agent runtime + state machine
PYTHONPATH=. pytest tests/test_agent_runtime.py -v

# Verification pipeline
PYTHONPATH=. pytest tests/test_verification.py -v

# Multi-agent orchestration
PYTHONPATH=. pytest tests/test_multi_agent.py -v

# Memory store
PYTHONPATH=. pytest tests/test_memory.py -v

# Retrieval
PYTHONPATH=. pytest tests/test_retrieval.py -v

# Full API (missions, approvals, skills, metrics)
PYTHONPATH=. pytest tests/test_missions_api.py tests/test_metrics.py -v

# Demo integration scenario
PYTHONPATH=. pytest tests/demo/ -v
```
