---
name: release-readiness
description: Assess whether a change is safe to release.
---

# release-readiness

## When to use

Use before deployment, merge, launch, publication, or handoff.

## Workflow

1. Check tests, migrations, configuration, dependencies, observability, security, documentation, and rollback.
2. Identify blockers separately from follow-up improvements.
3. Verify ownership and post-release monitoring.

## Output contract

A go/no-go assessment with blockers and rollback plan.

## Guardrails

- Load this skill only when it materially improves the task.
- Prefer concrete evidence over assumptions.
- Keep the result proportional to the user's requested depth.
- Do not repeat context that is already available unless it is needed for the output.
