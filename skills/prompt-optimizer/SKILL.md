---
name: prompt-optimizer
description: Rewrite a prompt to be clearer, shorter, testable, and less ambiguous while preserving intent.
---

# prompt-optimizer

## When to use

Use when a prompt is verbose, conflicting, underspecified, or expensive to run.

## Workflow

1. Extract objective, inputs, constraints, tools, and output format.
2. Remove duplicated instructions and resolve conflicts explicitly.
3. Add only missing constraints that materially improve execution.

## Output contract

An optimized prompt plus a short note on material changes.

## Guardrails

- Load this skill only when it materially improves the task.
- Prefer concrete evidence over assumptions.
- Keep the result proportional to the user's requested depth.
- Do not repeat context that is already available unless it is needed for the output.
