---
name: code-review
description: Review a change for concrete defects, regressions, security problems, and missing tests.
---

# Code review

Understand what the change is supposed to do before judging how it is written.

Read the surrounding code and tests when the diff alone is not enough to understand the behavior.

## Review order

1. correctness and edge cases;
2. security and permission boundaries;
3. data loss or compatibility risk;
4. concurrency, retries, and failure handling where relevant;
5. missing or misleading tests;
6. maintainability problems that are likely to cause real future mistakes;
7. style only when the repository has a clear convention or the style affects readability.

For every finding, be able to answer:

- what can go wrong;
- under which input or state;
- where the evidence is in the change;
- how the author could fix or test it.

Avoid speculative comments that cannot describe a failure mode. Avoid asking for unrelated cleanup just because the file is already being edited.

If no meaningful defects are found, say that instead of manufacturing low-value comments.

See also: `test-strategy`, `security-review`, `pull-request`.
