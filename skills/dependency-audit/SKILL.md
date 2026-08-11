---
name: dependency-audit
description: Evaluate dependencies for necessity, compatibility, maintenance, and risk.
---

# dependency-audit

## When to use

Use before adding, upgrading, or removing packages.

## Workflow

1. Check whether existing capabilities already solve the need.
2. Review version constraints, transitive impact, licensing, security, and runtime cost.
3. Prefer the smallest maintained dependency surface.

## Output contract

A dependency recommendation with tradeoffs.

## Guardrails

- Load this skill only when it materially improves the task.
- Prefer concrete evidence over assumptions.
- Keep the result proportional to the user's requested depth.
- Do not repeat context that is already available unless it is needed for the output.
