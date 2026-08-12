# Engineering notes

Use these notes for repository work, debugging, testing, refactors, CI, interfaces, and system design.

## Start by finding the change surface

Do not read the repository from top to bottom.

Find the entry point, the code path related to the task, its tests, and the configuration that controls it. Expand outward only when evidence requires it.

## Debug from a reproduction

A useful debugging loop is:

```text
reproduce -> narrow -> form one explanation -> run a discriminating check -> update the explanation
```

Do not change several unrelated things between observations. That makes a successful run hard to explain and a failed run hard to learn from.

## Fix the cause before the shape

Prefer the smallest change that fixes the verified cause and preserves existing behavior elsewhere.

A larger cleanup can be useful, but it should not be smuggled into a bug fix when it makes verification harder.

## Tests

Choose tests based on failure risk.

A focused regression test is usually the first check for a local bug. Broader tests matter when the change crosses package, process, API, or persistence boundaries.

A passing test is useful only if it exercises the behavior being claimed.

## Refactors

State which behavior must remain unchanged. Keep behavior-preserving changes separate from intentional behavior changes where possible.

If the refactor changes interfaces, data shape, error handling, timing, or side effects, treat those as behavior changes and test them explicitly.

## Review

Prioritize correctness, security, regressions, and missing tests over style preferences.

A review comment should explain the concrete failure mode, the evidence, and a practical fix. Avoid comments that amount to personal formatting preference unless the repository has an established rule.

## CI

When CI fails but local work passes, compare environment details first: runtime versions, dependency lockfiles, paths, services, environment variables, permissions, and caches.

Retrying a flaky-looking job is fine once; repeated retries are not a diagnosis.
