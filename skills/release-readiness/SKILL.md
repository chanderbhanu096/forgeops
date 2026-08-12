---
name: release-readiness
description: Check whether a change is safe to ship, not merely whether the build is green.
---

# Release readiness

Use this before a deployment, tagged release, or change that is difficult to undo.

## Check the change itself

- intended behavior is covered by the relevant tests;
- configuration changes are documented and have sane defaults;
- database or data migrations have been rehearsed where practical;
- backward compatibility is understood;
- security-sensitive changes received appropriate review;
- operational dashboards or alerts can reveal a bad rollout.

## Check the rollout

Know how the change will be enabled, how quickly it can be disabled, and what signal would trigger rollback.

A rollback plan should be specific enough to execute. “Revert if needed” is not a rollback plan when schema or external state has changed.

## Check user impact

Call out changed behavior, removed options, new permissions, migration steps, or anything users/operators need to do differently.

Do not claim readiness based only on CI. CI can prove useful things, but it cannot prove that a migration is reversible or that production credentials and dependencies are configured correctly.

See also: `security-review`, `observability-plan`, `git-commit`, `pull-request`.
