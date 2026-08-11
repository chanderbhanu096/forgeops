---
name: security-review
description: Review a design or change for exploitable behavior and unsafe defaults.
---

# security-review

## When to use

Use before release or for security-sensitive changes.

## Workflow

1. Trace untrusted input through authentication, authorization, storage, execution, and output.
2. Check secrets, injection, access control, data exposure, dependency risk, and abuse cases.
3. Prioritize realistic impact and concrete mitigations.

## Output contract

Severity-ranked security findings and mitigations.

## Guardrails

- Load this skill only when it materially improves the task.
- Prefer concrete evidence over assumptions.
- Keep the result proportional to the user's requested depth.
- Do not repeat context that is already available unless it is needed for the output.
