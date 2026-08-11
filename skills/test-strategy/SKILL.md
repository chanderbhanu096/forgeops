---
name: test-strategy
description: Choose the smallest effective set of tests for a change or system.
---

# test-strategy

## When to use

Use when deciding what to test and at which layer.

## Workflow

1. Map risks to unit, integration, contract, end-to-end, and manual checks.
2. Prefer fast deterministic tests for most behavior and reserve E2E for critical flows.
3. Include negative paths, boundaries, and failure recovery.

## Output contract

A risk-based test plan.

## Guardrails

- Load this skill only when it materially improves the task.
- Prefer concrete evidence over assumptions.
- Keep the result proportional to the user's requested depth.
- Do not repeat context that is already available unless it is needed for the output.
