---
name: skill-router
description: Pick the smallest useful set of skills for the task at hand.
---

# Skill router

Use this file when it is not obvious which skill should handle a task.

The basic rule is simple: pick one primary skill for the work being done now. Add at most two related skills if they cover a separate concern. Do not load the whole library.

## First decide what kind of work this is

A task normally starts in one of these places:

- understand something
- explore options
- make a decision
- plan work
- implement a change
- verify a result
- deliver or publish a change
- hand work to someone else

Choose the skill whose output is closest to what the user actually asked for.

## Shared files

Every skill can use `skills/_shared/CORE.md` for common rules around evidence, tool calls, writes, retries, and verification.

Then use the shared file for the relevant area:

- context and prompts: `_shared/CONTEXT.md`
- planning and decisions: `_shared/THINKING.md`
- research: `_shared/RESEARCH.md`
- software work: `_shared/ENGINEERING.md`
- release, security, and operational work: `_shared/DELIVERY.md`

These are supporting notes, not prerequisites that must be copied into the prompt every time. If the current task does not need a shared section, do not load it.

## Common routes

Ambiguous request:

```text
problem-framing -> requirements-clarifier -> task-decomposer
```

New idea:

```text
brainstorm -> idea-evaluator -> experiment-design
```

Research question:

```text
research-plan -> retrieval-first -> source-synthesizer -> fact-check
```

Bug:

```text
codebase-orient -> debug -> minimal-fix -> test-strategy
```

Refactor:

```text
codebase-orient -> refactor-safely -> test-strategy -> code-review
```

New API or service:

```text
requirements-clarifier -> api-design/system-design -> threat-model -> test-strategy
```

Release:

```text
code-review -> security-review -> release-readiness -> git-commit -> pull-request
```

Long session:

```text
token-budget -> context-compact -> handover
```

## A few things not to do

- Do not load skills just because their names sound related.
- Do not repeat a skill if its result is already in the context.
- Do not keep exploration notes in the active prompt once the task has moved to implementation.
- Do not continue through a chain after the requested result is finished.
- Do not use extra skills as a substitute for asking one necessary question.

When a phase is finished, keep the useful state, drop the rest, and choose a new primary skill only if more work remains.
