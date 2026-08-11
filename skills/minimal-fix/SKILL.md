---
name: minimal-fix
description: Make the smallest safe change that solves a verified problem.
---

# minimal-fix

## When to use

Use when reliability and low regression risk matter more than broad cleanup.

## Workflow

1. Touch only artifacts required for the root cause.
2. Avoid unrelated refactors or dependency changes.
3. Add the narrowest regression test that would have caught the issue.

## Output contract

A minimal patch with focused validation.

## Guardrails

- Load this skill only when it materially improves the task.
- Prefer concrete evidence over assumptions.
- Keep the result proportional to the user's requested depth.
- Do not repeat context that is already available unless it is needed for the output.
