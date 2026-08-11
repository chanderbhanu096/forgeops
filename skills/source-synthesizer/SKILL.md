---
name: source-synthesizer
description: Combine multiple sources into one coherent answer without flattening disagreements.
---

# source-synthesizer

## When to use

Use after gathering evidence from several documents or references.

## Workflow

1. Group evidence by claim rather than by source.
2. Separate consensus, disagreement, uncertainty, and inference.
3. Prefer stronger and more direct evidence when sources conflict.

## Output contract

A synthesis with traceable claims and unresolved uncertainty.

## Guardrails

- Load this skill only when it materially improves the task.
- Prefer concrete evidence over assumptions.
- Keep the result proportional to the user's requested depth.
- Do not repeat context that is already available unless it is needed for the output.
