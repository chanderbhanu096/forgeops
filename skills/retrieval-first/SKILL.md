---
name: retrieval-first
description: Retrieve targeted evidence before reasoning from broad memory or loading large context.
---

# retrieval-first

## When to use

Use when files, repositories, logs, or external sources contain the answer.

## Workflow

1. Form the narrowest useful query first.
2. Read the smallest relevant range or artifact.
3. Expand retrieval only when the current evidence cannot resolve the question.

## Output contract

A focused evidence set ready for reasoning.

## Guardrails

- Load this skill only when it materially improves the task.
- Prefer concrete evidence over assumptions.
- Keep the result proportional to the user's requested depth.
- Do not repeat context that is already available unless it is needed for the output.
