---
name: api-design
description: Design a clear, evolvable interface contract before implementation.
---

# api-design

## When to use

Use for HTTP, RPC, event, tool, or internal service interfaces.

## Workflow

1. Define inputs, outputs, errors, authentication, idempotency, and pagination where relevant.
2. Design compatibility and versioning behavior.
3. Provide examples for normal and failure paths.

## Output contract

An implementation-ready interface contract.

## Guardrails

- Load this skill only when it materially improves the task.
- Prefer concrete evidence over assumptions.
- Keep the result proportional to the user's requested depth.
- Do not repeat context that is already available unless it is needed for the output.
