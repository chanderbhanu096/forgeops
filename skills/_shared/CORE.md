# Common working rules

These notes apply to most skills in this directory. They are here so the same rules do not have to be repeated in every file.

## Before doing anything expensive

Make sure you know:

- what the user is asking for;
- what would count as done;
- which constraints would change the answer;
- which facts are known and which are guesses.

If a missing fact can be read from the repository, a document, or another authoritative source, look it up instead of asking the user to repeat it.

## Keep facts and guesses separate

It helps to treat information as one of four things:

- **observed** - read directly from a source or command output;
- **derived** - calculated from observed information;
- **inferred** - a reasonable explanation that has not been confirmed;
- **unknown** - still missing.

Do not quietly promote an inference into a fact because it makes the next step easier.

## Use tools in a sensible order

Prefer read-only work first.

A common sequence is:

```text
inspect -> narrow the question -> run a check -> make a change -> verify the change
```

Before a write, know the exact target and expected effect. After a write, read back or test the result when that is practical.

If a tool returns much more data than needed, keep the useful excerpt and leave the rest out of the active context.

## Prefer tests that can prove something

When several checks are available, start with the cheapest check that can distinguish between the likely explanations.

For a bug this may be a focused test. For research it may be one primary source. For a deployment issue it may be the first failing health check rather than a full redeploy.

Passing an unrelated check is not evidence for the thing being investigated.

## Retries

Do not repeat the same failed action without changing anything.

Before retrying, classify the failure:

- bad input;
- missing permission or credential;
- unavailable dependency;
- transient service failure;
- wrong assumption;
- actual product defect.

Retry only when there is a reason the next attempt should behave differently.

## Decisions under uncertainty

Write down assumptions when both of these are true:

1. the assumption affects the result in a meaningful way; and
2. it cannot be verified cheaply right now.

Prefer reversible choices when uncertainty is high. Spend more time on a decision when it is costly to undo, changes public behavior, affects security, or commits a lot of future work.

## Keep context under control

Do not paste entire logs, files, or search results when a few lines answer the question.

Once a decision is settled, keep the decision and the reason. Drop most of the path taken to get there unless a failed path contains useful negative knowledge.

If a new phase begins, compact the previous phase before loading new material.

## Before saying the work is done

Check the result against the request.

For code or repository work, ask:

- was the intended file or behavior actually changed?
- were the relevant checks run?
- is the working tree or branch in the expected state?
- did the change introduce a new assumption that should be documented?

For research or analysis, ask:

- are important claims supported?
- are disagreements between sources visible?
- are limitations stated where they matter?

If the evidence is not strong enough, say what is missing instead of filling the gap with confidence.

## Stop conditions

Stop when the requested artifact exists and the available evidence is sufficient for the requested confidence level.

Ask for help or escalate when a missing fact is high impact and cannot be inferred safely, when permission is missing, or when a destructive/write target is ambiguous.
