---
name: git-commit
description: Create a focused commit that represents one coherent change.
---

# git-commit

## When to use

Use after implementation and validation.

## Workflow

1. Inspect the diff and exclude unrelated changes.
2. Ensure required checks pass before committing.
3. Write a message that describes behavior or intent, not mechanics.

## Output contract

One clean commit with validation summary.

## Guardrails

- Load this skill only when it materially improves the task.
- Prefer concrete evidence over assumptions.
- Keep the result proportional to the user's requested depth.
- Do not repeat context that is already available unless it is needed for the output.
