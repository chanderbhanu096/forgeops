---
name: ci-debug
description: Diagnose CI failures by reproducing the actual job conditions.
---

# ci-debug

## When to use

Use when local checks pass but automation fails, or a workflow is red.

## Workflow

1. Inspect the failing job, command, environment, and first real error.
2. Compare runtime, dependency versions, paths, secrets, caches, and services with local assumptions.
3. Fix determinism problems before adding retries.

## Output contract

CI root cause, fix, and verification commands.

## Guardrails

- Load this skill only when it materially improves the task.
- Prefer concrete evidence over assumptions.
- Keep the result proportional to the user's requested depth.
- Do not repeat context that is already available unless it is needed for the output.
