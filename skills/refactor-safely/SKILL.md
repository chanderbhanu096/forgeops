---
name: refactor-safely
description: Improve structure without changing intended behavior.
---

# refactor-safely

## When to use

Use for maintainability cleanup after behavior is already understood.

## Workflow

1. Establish tests or behavior checks before refactoring.
2. Make small mechanical transformations with clear boundaries.
3. Run equivalence checks after each meaningful step.

## Output contract

A behavior-preserving refactor with evidence.

## Guardrails

- Load this skill only when it materially improves the task.
- Prefer concrete evidence over assumptions.
- Keep the result proportional to the user's requested depth.
- Do not repeat context that is already available unless it is needed for the output.
