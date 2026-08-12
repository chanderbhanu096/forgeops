---
name: handover
description: Leave enough state for another person or agent to continue without redoing the investigation.
---

# Handover

Use this at a session boundary, ownership change, or before context is likely to be lost.

A handover should save restart time. It does not need to preserve the entire history.

## Include

- what we are trying to finish;
- what is already done;
- where the relevant files, branches, commits, artifacts, or dashboards are;
- decisions that should not be reopened without new evidence;
- the last useful failure or blocker;
- approaches already tried and why they were abandoned;
- the next one to three actions;
- the command, test, or observation that confirms success.

Do not include secrets. Refer to the secret name or storage location instead.

## A useful shape

```text
Goal
Current state
Important files/IDs
Decisions
What failed
Next actions
How to verify
```

Avoid entries such as “continue debugging the API.” Write the latest observed failure and the first place to look next.

If a receiver can start work from the handover without asking what happened before, it is good enough.

See also: `context-compact`, `decision-record`, `execution-plan`.
