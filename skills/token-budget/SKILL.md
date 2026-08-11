---
name: token-budget
description: Allocate context and output tokens to the parts of a task that create the most value.
---

# token-budget

## When to use

Use for long, multi-step, retrieval-heavy, or tool-heavy work.

## Workflow

1. Reserve space for the goal, constraints, evidence, and final verification.
2. Summarize intermediate results instead of replaying raw outputs.
3. Spend more tokens only when uncertainty, risk, or complexity justifies it.

## Output contract

A lean token plan and compression points.

## Guardrails

- Load this skill only when it materially improves the task.
- Prefer concrete evidence over assumptions.
- Keep the result proportional to the user's requested depth.
- Do not repeat context that is already available unless it is needed for the output.
