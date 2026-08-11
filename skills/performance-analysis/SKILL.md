---
name: performance-analysis
description: Find performance bottlenecks using measurement before optimization.
---

# performance-analysis

## When to use

Use for latency, throughput, memory, CPU, I/O, or cost problems.

## Workflow

1. Define the metric, workload, and target.
2. Profile to locate the dominant bottleneck.
3. Optimize the bottleneck, then measure again and check regressions elsewhere.

## Output contract

Measured bottleneck, change, and before/after evidence.

## Guardrails

- Load this skill only when it materially improves the task.
- Prefer concrete evidence over assumptions.
- Keep the result proportional to the user's requested depth.
- Do not repeat context that is already available unless it is needed for the output.
