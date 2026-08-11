---
name: response-compressor
description: Reduce an answer while preserving actionable content and important caveats.
---

# response-compressor

## When to use

Use when an answer is correct but too long or repetitive.

## Workflow

1. Keep the conclusion, essential reasoning, actions, and critical caveats.
2. Collapse repeated examples and merge overlapping sections.
3. Prefer dense prose or compact structure only when it improves scanability.

## Output contract

A shorter answer with no material information loss.

## Guardrails

- Load this skill only when it materially improves the task.
- Prefer concrete evidence over assumptions.
- Keep the result proportional to the user's requested depth.
- Do not repeat context that is already available unless it is needed for the output.
