---
name: observability-plan
description: Define telemetry that makes system behavior and failures diagnosable.
---

# observability-plan

## When to use

Use when building or operating services, agents, or workflows.

## Workflow

1. Identify key user journeys and failure modes.
2. Choose metrics, logs, traces, correlation identifiers, and useful dimensions.
3. Define alerts on symptoms and objectives, not noisy internals.

## Output contract

An observability map with signals and alert conditions.

## Guardrails

- Load this skill only when it materially improves the task.
- Prefer concrete evidence over assumptions.
- Keep the result proportional to the user's requested depth.
- Do not repeat context that is already available unless it is needed for the output.
