---
name: test-strategy
description: Choose the smallest useful set of tests for the behavior and risks of a change.
---

# Test strategy

Start from what could break, not from a generic pyramid.

## Pick tests by boundary

- pure logic: focused unit tests;
- database or filesystem behavior: integration tests around the real boundary;
- API contracts: request/response and error-path tests;
- asynchronous work: ordering, retries, duplication, and idempotency tests;
- UI changes: component behavior plus one end-to-end path when integration is the risk;
- bug fixes: reproduce the old failure first when practical.

Use broad suites after focused checks, not instead of them.

A test is valuable when a realistic regression would make it fail for the right reason.

## Watch for

- tests that only restate implementation details;
- mocks that remove the behavior being tested;
- assertions so weak that the old bug would still pass;
- flaky timing assumptions;
- large end-to-end tests for behavior that can be checked deterministically lower down.

Stop when the important behavior and failure boundaries are covered well enough for the cost and risk of the change.

See also: `test-failure-triage`, `minimal-fix`, `release-readiness`.
