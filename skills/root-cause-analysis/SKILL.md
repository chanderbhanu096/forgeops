---
name: root-cause-analysis
description: Find the underlying cause of a failure instead of stopping at the first visible error.
---

# root-cause-analysis

## When to use

Use for recurring, multi-layer, or high-impact problems.

## Workflow

1. Build a timeline and causal chain from evidence.
2. Separate trigger, contributing factors, and root cause.
3. Propose corrective and preventive actions.

## Output contract

A causal explanation with confidence and prevention steps.

## Guardrails

- Load this skill only when it materially improves the task.
- Prefer concrete evidence over assumptions.
- Keep the result proportional to the user's requested depth.
- Do not repeat context that is already available unless it is needed for the output.
