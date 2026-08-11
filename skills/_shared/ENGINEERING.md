---
name: engineering-protocol
scope: category
---

# Engineering Protocol

Applies to: `codebase-orient`, `debug`, `root-cause-analysis`, `minimal-fix`, `refactor-safely`, `code-review`, `test-strategy`, `test-failure-triage`, `ci-debug`, `dependency-audit`, `api-design`, `system-design`, `architecture-tradeoffs`, `data-modeling`.

## Objective

Make the smallest correct engineering decision with explicit invariants, realistic failure behavior, and verification proportional to blast radius.

## Codebase orientation

Before editing unfamiliar code, identify:

- entry point;
- execution path relevant to the task;
- state boundaries;
- configuration that changes runtime behavior;
- external interfaces;
- existing tests and intended behavior;
- generated or vendor-managed files that should not be edited manually.

Stop orienting when the likely change surface and validation path are clear.

## Debugging loop

Use:

`reproduce -> locate earliest divergence -> rank hypotheses -> discriminating test -> verified cause -> minimal fix -> regression test`.

Do not perform shotgun edits. One causal variable per diagnostic experiment whenever practical.

## Invariant-first design

For APIs, schemas, and architecture, write down the invariants that must remain true under:

- retries;
- duplicate requests;
- partial failure;
- concurrency;
- stale reads;
- dependency outage;
- migration;
- rollback.

Choose components only after these constraints and workload characteristics are explicit.

## Test economics

Test at the lowest layer that reliably catches the target failure mode. Use integration/contract tests at boundaries where mocks can hide incompatibility. Keep end-to-end tests focused on critical journeys.

Coverage percentage is not a substitute for risk coverage.

## Refactoring rule

Separate behavior changes from structure changes. Characterize under-specified behavior before refactoring it. Stop when the targeted maintainability problem is solved.

## Review severity

A review finding should include:

- concrete failure mode;
- reachable conditions;
- impact;
- evidence/confidence;
- practical remediation.

Do not bury correctness defects beneath style comments.
