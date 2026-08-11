---
name: assumption-audit
description: Expose assumptions that could invalidate a plan, analysis, or implementation.
---

# assumption-audit

## When to use

Use before high-cost work or when confidence depends on unverified beliefs.

## Workflow

1. List explicit and implicit assumptions.
2. Rank them by impact and uncertainty.
3. Verify the highest-risk assumptions first or mark them clearly as unresolved.

## Output contract

A prioritized assumption list with validation actions.

## Guardrails

- Load this skill only when it materially improves the task.
- Prefer concrete evidence over assumptions.
- Keep the result proportional to the user's requested depth.
- Do not repeat context that is already available unless it is needed for the output.
