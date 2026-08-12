# ForgeOps

ForgeOps is a small experiment in using language models for repository investigation without letting the model quietly make things up or change a project on its own.

The main use case is a repository review. Give ForgeOps a GitHub repository, let it inspect the code, collect evidence, and produce a report. If a change is needed, that becomes a separate step and should require an explicit approval.

There is a live demo at:

https://forgeops-staging-web.greenrock-70958585.northeurope.azurecontainerapps.io

## What it does

A mission usually looks like this:

1. identify the repository and revision to inspect;
2. read the files needed for the question;
3. keep findings tied to source evidence;
4. run deterministic checks when they are available;
5. stop before a write or deployment unless that action has been approved.

The project keeps checkpoints in PostgreSQL so a failed mission can be inspected instead of disappearing with the process that ran it.

The current implementation has a FastAPI backend, a Next.js interface, model-provider adapters, GitHub tooling, and a small verification layer around repository work.

## Try it locally

You need Docker and Docker Compose.

```bash
git clone https://github.com/chanderbhanu096/forgeops.git
cd forgeops
cp .env.example .env
docker compose up --build
```

Open `http://localhost:3000`.

The demo provider works without an external model key. Real providers can be configured in `.env`.

## Example mission

```text
Review https://github.com/OWNER/REPOSITORY.

Inspect the main branch in read-only mode. Show which files you used for each
finding and keep assumptions separate from confirmed facts. Do not create a
patch or claim that tests passed unless those tests were actually run. Stop
before making a repository change.
```

This example is intentionally strict. It is useful when testing whether a model is following repository evidence instead of filling in missing details from prior knowledge.

## Repository layout

```text
apps/api/        FastAPI service and mission logic
apps/web/        Next.js interface
services/        supporting services and integrations
infra/           deployment and infrastructure files
docs/            longer design and operating notes
scripts/         local and CI helper scripts
skills/          reusable instructions for common agent tasks
```

## Model providers

Provider configuration stays on the server. The UI only receives provider and model names, not secret values.

The code currently supports several provider styles, including OpenAI-compatible endpoints. Check `.env.example` for the variables used by the current version rather than relying on this README for a complete list.

## GitHub access

For repository investigation, read-only GitHub permissions are enough and are the preferred starting point.

If write support is enabled, keep that permission separate from ordinary inspection and approve the exact target before using it. In particular, repository, branch, patch, and pull-request scope should be known before a write happens.

GitHub App credentials and model keys belong in local secrets, GitHub Actions secrets, or the deployment platform. Do not put them in the repository.

## Checks

The project uses the same commands locally and in CI.

Backend:

```bash
cd apps/api
poetry install --with dev
poetry run ruff check forgeops
poetry run pytest tests/ -v
```

Frontend:

```bash
cd apps/web
npm ci
npm run lint
npm run type-check
npm run build
```

Compose:

```bash
docker compose config --quiet
docker compose build --pull
```

## How repository reviews are handled

The useful part of ForgeOps is less the model call and more the bookkeeping around it.

A repository finding should have a source. A proposed fix should be distinguishable from a confirmed bug. A successful verification should come from an actual command or check. If repository access fails halfway through a mission, the mission should say that instead of finishing a confident report from partial evidence.

That is the behavior the project is trying to make boring and repeatable.

## Skills

`skills/` contains reusable notes for recurring work such as debugging, planning, code review, research, context compaction, and handoff.

They are deliberately loaded on demand. They are not meant to be concatenated into one giant prompt. Start with [`skills/SKILL.md`](skills/SKILL.md), which explains the routing convention.

## Current limitations

ForgeOps is still a project under active development. A few boundaries are worth keeping in mind:

- access to a repository does not mean every external dependency or service can be reproduced locally;
- model output is not treated as verification;
- a repository review can still miss a problem if the relevant evidence was never retrieved;
- provider behavior differs, especially around tool calling and long context;
- the approval model is only useful if write-capable integrations are configured with appropriately narrow permissions.

These are design constraints rather than problems the prompt alone can solve.

## License

See [LICENSE](LICENSE).
