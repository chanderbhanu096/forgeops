---
name: structured-extractor
description: Turn unstructured content into a reliable schema.
---

# structured-extractor

## When to use

Use when converting prose, logs, tickets, emails, or documents into structured fields.

## Workflow

1. Define the schema before extraction.
2. Use null or unknown when a field is absent; never fabricate.
3. Preserve source wording for fields where exactness matters.

## Output contract

Structured data plus warnings for ambiguous fields.

## Guardrails

- Load this skill only when it materially improves the task.
- Prefer concrete evidence over assumptions.
- Keep the result proportional to the user's requested depth.
- Do not repeat context that is already available unless it is needed for the output.
