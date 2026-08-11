---
name: fact-check
description: Verify factual claims and distinguish known, inferred, and unknown information.
---

# fact-check

## When to use

Use before publishing high-confidence claims or when accuracy is disputed.

## Workflow

1. Break the text into checkable claims.
2. Verify important claims against appropriate authoritative evidence.
3. Correct errors and label uncertainty instead of guessing.

## Output contract

A corrected claim set with confidence notes.

## Guardrails

- Load this skill only when it materially improves the task.
- Prefer concrete evidence over assumptions.
- Keep the result proportional to the user's requested depth.
- Do not repeat context that is already available unless it is needed for the output.
