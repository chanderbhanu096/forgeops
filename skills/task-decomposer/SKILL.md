---
name: task-decomposer
description: Break a complex goal into small, ordered, verifiable units of work.
---

# task-decomposer

## When to use

Use when a task spans multiple artifacts, systems, roles, or stages.

## Workflow

1. Identify dependencies and the critical path.
2. Make each task independently understandable and testable.
3. Separate must-have work from optional follow-ups.

## Output contract

An ordered execution plan with checkpoints.

## Guardrails

- Load this skill only when it materially improves the task.
- Prefer concrete evidence over assumptions.
- Keep the result proportional to the user's requested depth.
- Do not repeat context that is already available unless it is needed for the output.
