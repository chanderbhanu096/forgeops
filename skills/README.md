# General-Purpose LLM Skills

This directory is a model-agnostic skill library for agents and LLM workflows. Each skill lives in its own folder as `skills/<name>/SKILL.md`.

## Loading rule

Do not load all skills by default. First classify the task, then load only the 1-3 skills that materially help. Prefer `context-router` when unsure. Use `context-compact` or `handover` before context grows too large.

## Routing index

### Context & token efficiency
- `context-compact`
- `handover`
- `prompt-optimizer`
- `context-router`
- `token-budget`
- `response-compressor`
- `progressive-disclosure`
- `retrieval-first`
- `tool-call-planner`
- `stop-condition`

### Thinking & planning
- `brainstorm`
- `idea-evaluator`
- `problem-framing`
- `requirements-clarifier`
- `task-decomposer`
- `execution-plan`
- `project-kickoff`
- `decision-record`
- `assumption-audit`
- `risk-register`

### Research & knowledge
- `research-plan`
- `source-synthesizer`
- `fact-check`
- `summarizer`
- `structured-extractor`
- `experiment-design`
- `retrospective`
- `learning-mode`

### Engineering
- `codebase-orient`
- `debug`
- `root-cause-analysis`
- `minimal-fix`
- `refactor-safely`
- `code-review`
- `test-strategy`
- `test-failure-triage`
- `ci-debug`
- `dependency-audit`
- `api-design`
- `system-design`
- `architecture-tradeoffs`
- `data-modeling`

### Quality, safety & delivery
- `security-review`
- `threat-model`
- `performance-analysis`
- `observability-plan`
- `documentation-writer`
- `release-readiness`
- `git-commit`
- `pull-request`

## Composition examples

- Long task getting expensive: `context-router` -> `token-budget` -> `context-compact`
- Start a new idea: `brainstorm` -> `idea-evaluator` -> `project-kickoff`
- Ambiguous request: `problem-framing` -> `requirements-clarifier` -> `task-decomposer`
- Research: `research-plan` -> `retrieval-first` -> `source-synthesizer` -> `fact-check`
- Bug fix: `codebase-orient` -> `debug` -> `minimal-fix` -> `test-strategy`
- Design work: `requirements-clarifier` -> `system-design` -> `architecture-tradeoffs` -> `threat-model`
- Release: `code-review` -> `security-review` -> `release-readiness` -> `git-commit` -> `pull-request`
- Session boundary: `context-compact` -> `handover`

## Skill design principles

Skills should be narrow, reusable, evidence-oriented, and cheap to load. A skill should define when it applies, a short workflow, an output contract, and guardrails. Project-specific knowledge belongs in project documentation or project-local skills, not in this general-purpose library.
