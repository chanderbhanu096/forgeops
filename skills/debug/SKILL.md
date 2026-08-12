---
name: debug
description: Find the cause of a failure by narrowing it with reproducible evidence.
---

# Debug

Start with the failure you can actually observe.

If it cannot be reproduced, first capture the exact input, environment, error, timing, and state that were present when it happened. Do not jump straight to a fix based on the error message alone.

## Loop

```text
reproduce
  -> narrow the failing layer
  -> write one likely explanation
  -> choose a check that can disprove it
  -> update the explanation
```

Prefer checks that separate two explanations. Adding more logs is useful only when those logs answer a specific question.

Once the cause is known, make the smallest change that addresses it. Then rerun the original reproduction before running broader tests.

## Common traps

- changing several things between runs;
- assuming the last stack-frame is the root cause;
- treating a retry that happened to pass as a fix;
- debugging the local environment when only CI fails, or vice versa;
- fixing the symptom while the bad state can still be created elsewhere.

Add a regression test when the failure can be captured cheaply and the bug could return unnoticed.

See also: `root-cause-analysis`, `minimal-fix`, `test-strategy`, `ci-debug`.
