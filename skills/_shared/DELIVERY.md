---
name: delivery-quality-protocol
scope: category
---

# Quality, Security, Operations & Delivery Protocol

Applies to: `security-review`, `threat-model`, `performance-analysis`, `observability-plan`, `documentation-writer`, `release-readiness`, `git-commit`, `pull-request`.

## Objective

Move validated work into use safely, with known risk, observable behavior, and a credible rollback path.

## Security lens

For exposed or sensitive changes, map:

- assets;
- principals;
- entry points;
- trust boundaries;
- authentication;
- authorization;
- sensitive data flow;
- secret handling;
- abuse/resource-exhaustion paths;
- dependency/supply-chain exposure.

Rank findings by exploitability, reachability, impact, and confidence. Prefer remediations that close the vulnerable path and can be regression-tested.

## Performance lens

Never optimize before measuring a representative workload. Compare distributions, including tail latency when relevant. Control dataset size, cache state, warmup, concurrency, and environment between before/after measurements.

## Observability lens

Instrument the questions an operator must answer during failure. Alerts require an owner and an action. Prefer symptom/SLO-based alerts to noisy internal anomalies.

## Documentation quality

Documentation is correct only when commands, defaults, paths, configuration, and failure behavior match the current implementation. Include a verification step so readers can confirm success.

## Release gate

A release decision should explicitly cover:

- acceptance criteria;
- test/quality evidence;
- compatibility and migration;
- security review where relevant;
- operational ownership;
- telemetry and health signals;
- rollout strategy;
- abort threshold;
- rollback mechanism;
- residual risks.

A green test suite alone is not release readiness.

## Git delivery

Before commit or PR:

- inspect final diff;
- exclude unrelated user changes;
- confirm required checks pass;
- ensure one coherent change story;
- state motivation/root cause, behavior impact, risks, and validation;
- verify the resulting commit/branch/PR points to the intended state.
