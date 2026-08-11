---
name: code-review
description: Review a change for correctness, regressions, security, maintainability, and missing tests.
---

# code-review

## When to use

Use for pull requests, patches, or pre-merge review.

## Workflow

1. Understand intended behavior before judging implementation.
2. Prioritize concrete defects over stylistic preference.
3. For each finding, explain impact, evidence, and a practical fix.

## Output contract

A severity-ranked review with actionable findings.

## Guardrails

- Load this skill only when it materially improves the task.
- Prefer concrete evidence over assumptions.
- Keep the result proportional to the user's requested depth.
- Do not repeat context that is already available unless it is needed for the output.
