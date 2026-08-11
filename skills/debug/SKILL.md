---
name: debug
description: Diagnose a defect systematically using evidence rather than trial-and-error edits.
---

# debug

## When to use

Use when behavior differs from expectations.

## Workflow

1. Reproduce or precisely characterize the failure.
2. Narrow the failing layer using logs, tests, state, and minimal experiments.
3. Fix the verified cause and add regression coverage where practical.

## Output contract

Root cause, minimal fix, and validation evidence.

## Guardrails

- Load this skill only when it materially improves the task.
- Prefer concrete evidence over assumptions.
- Keep the result proportional to the user's requested depth.
- Do not repeat context that is already available unless it is needed for the output.
