---
name: requirements-clarifier
description: Convert ambiguous needs into implementable requirements without over-specifying.
---

# requirements-clarifier

## When to use

Use before implementation when acceptance criteria or constraints are unclear.

## Workflow

1. Extract functional requirements, non-functional requirements, constraints, and edge cases.
2. Mark assumptions instead of silently inventing requirements.
3. Turn important requirements into observable acceptance criteria.

## Output contract

A requirements brief with assumptions and acceptance criteria.

## Guardrails

- Load this skill only when it materially improves the task.
- Prefer concrete evidence over assumptions.
- Keep the result proportional to the user's requested depth.
- Do not repeat context that is already available unless it is needed for the output.
