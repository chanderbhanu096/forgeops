# Skills

This directory is a collection of reusable working notes for common agent tasks.

They started as a way to avoid rewriting the same instructions for debugging, code review, research, planning, and context cleanup in every prompt. The files are intentionally small enough to load only when they are useful.

## How to use them

Start with [`SKILL.md`](SKILL.md). It acts as a simple router.

In most cases one skill is enough. Add a second or third only when it handles a different part of the task. Loading the whole directory usually makes the prompt worse, not better.

For example:

```text
bug report
  -> codebase-orient
  -> debug
  -> minimal-fix
  -> test-strategy
```

or:

```text
long session
  -> context-compact
  -> handover
```

The arrows do not mean every step is mandatory. Stop once the requested work is done.

## Shared notes

The `_shared/` files hold rules that would otherwise be copied into many skills:

- `CORE.md` - evidence, tool use, retries, and verification
- `CONTEXT.md` - context size, retrieval, and handoff
- `THINKING.md` - framing, options, decisions, and risk
- `RESEARCH.md` - sources, claims, contradictions, and experiments
- `ENGINEERING.md` - debugging, tests, refactors, and review
- `DELIVERY.md` - security, releases, documentation, and repository writes

These files are not meant to turn the skills into a formal framework. They are just common conventions.

## Skill groups

Context and prompt work:

`context-compact`, `handover`, `prompt-optimizer`, `context-router`, `token-budget`, `response-compressor`, `progressive-disclosure`, `retrieval-first`, `tool-call-planner`, `stop-condition`

Planning and decisions:

`brainstorm`, `idea-evaluator`, `problem-framing`, `requirements-clarifier`, `task-decomposer`, `execution-plan`, `project-kickoff`, `decision-record`, `assumption-audit`, `risk-register`

Research:

`research-plan`, `source-synthesizer`, `fact-check`, `summarizer`, `structured-extractor`, `experiment-design`, `retrospective`, `learning-mode`

Engineering:

`codebase-orient`, `debug`, `root-cause-analysis`, `minimal-fix`, `refactor-safely`, `code-review`, `test-strategy`, `test-failure-triage`, `ci-debug`, `dependency-audit`, `api-design`, `system-design`, `architecture-tradeoffs`, `data-modeling`

Delivery and operations:

`security-review`, `threat-model`, `performance-analysis`, `observability-plan`, `documentation-writer`, `release-readiness`, `git-commit`, `pull-request`

## Writing a new skill

A useful skill should answer a few practical questions:

- When is this file worth loading?
- What information is needed before starting?
- What order should the work happen in?
- Which mistakes are common here?
- What should the result look like?
- When should the agent stop or ask for help?

If the file cannot answer those questions, it is probably still a note rather than a reusable skill. That is fine; not every note needs to become a skill.
