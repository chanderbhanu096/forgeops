---
name: test-failure-triage
description: Classify failing tests quickly and avoid fixing the wrong thing.
---

# test-failure-triage

## When to use

Use when a suite has one or more failures.

## Workflow

1. Separate product defects, test defects, flaky behavior, environment issues, and dependency issues.
2. Start with the first causal failure rather than downstream noise.
3. Re-run the smallest reproducer before broad suites.

## Output contract

Failure classification, likely cause, and next diagnostic step.

## Guardrails

- Load this skill only when it materially improves the task.
- Prefer concrete evidence over assumptions.
- Keep the result proportional to the user's requested depth.
- Do not repeat context that is already available unless it is needed for the output.
