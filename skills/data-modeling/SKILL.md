---
name: data-modeling
description: Design data structures around access patterns, invariants, and lifecycle.
---

# data-modeling

## When to use

Use for relational, document, event, analytical, or in-memory models.

## Workflow

1. Identify entities, relationships, ownership, cardinality, and invariants.
2. Model keys, constraints, history, deletion, and evolution.
3. Validate the model against real read and write patterns.

## Output contract

A schema proposal with invariants and access-pattern rationale.

## Guardrails

- Load this skill only when it materially improves the task.
- Prefer concrete evidence over assumptions.
- Keep the result proportional to the user's requested depth.
- Do not repeat context that is already available unless it is needed for the output.
