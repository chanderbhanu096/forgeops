---
name: context-router
description: Select only the context and skills needed for the current task.
---

# context-router

## When to use

Use before loading large histories, documents, tools, or many skills.

## Workflow

1. Classify the task and identify the minimum information required.
2. Load narrow sources first; expand only when evidence is insufficient.
3. Avoid carrying unrelated prior context into the task.

## Output contract

A minimal context plan naming what to load and what to ignore.

## Guardrails

- Load this skill only when it materially improves the task.
- Prefer concrete evidence over assumptions.
- Keep the result proportional to the user's requested depth.
- Do not repeat context that is already available unless it is needed for the output.
