---
name: architecture-tradeoffs
description: Compare architectural choices using the constraints that actually matter.
---

# architecture-tradeoffs

## When to use

Use when several designs could work.

## Workflow

1. Name decision drivers and hard constraints.
2. Compare complexity, cost, latency, scalability, operability, security, and reversibility.
3. Prefer the simplest option that satisfies current requirements.

## Output contract

A recommendation with rejected alternatives and reversal triggers.

## Guardrails

- Load this skill only when it materially improves the task.
- Prefer concrete evidence over assumptions.
- Keep the result proportional to the user's requested depth.
- Do not repeat context that is already available unless it is needed for the output.
