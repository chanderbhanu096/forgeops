---
name: tool-call-planner
description: Minimize tool calls while preserving correctness and traceability.
---

# tool-call-planner

## When to use

Use before workflows involving multiple searches, files, APIs, or repositories.

## Workflow

1. Batch independent reads when possible.
2. Avoid rediscovering information already returned by tools.
3. Use expensive or mutating calls only after cheap reads establish the target.

## Output contract

A minimal ordered tool-call plan.

## Guardrails

- Load this skill only when it materially improves the task.
- Prefer concrete evidence over assumptions.
- Keep the result proportional to the user's requested depth.
- Do not repeat context that is already available unless it is needed for the output.
