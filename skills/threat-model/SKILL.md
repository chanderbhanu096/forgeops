---
name: threat-model
description: Model what can go wrong before implementation or release.
---

# threat-model

## When to use

Use for new systems, trust-boundary changes, sensitive data, or privileged capabilities.

## Workflow

1. Identify assets, actors, trust boundaries, entry points, and abuse goals.
2. Enumerate threats and rank by likelihood and impact.
3. Map high-priority threats to preventive, detective, and recovery controls.

## Output contract

A practical threat model and control plan.

## Guardrails

- Load this skill only when it materially improves the task.
- Prefer concrete evidence over assumptions.
- Keep the result proportional to the user's requested depth.
- Do not repeat context that is already available unless it is needed for the output.
