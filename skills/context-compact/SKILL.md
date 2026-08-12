---
name: context-compact
description: Reduce a long working context without losing the details needed to continue the job.
---

# Context compact

Use this when the conversation or working notes have become large enough that the same facts keep getting repeated.

The result is not a summary for a reader. It is a replacement working state for the next turn or the next person.

## Keep

- the current goal and what counts as finished;
- hard constraints and user preferences;
- decisions that still affect the work;
- exact paths, commands, IDs, versions, numbers, and URLs that will be needed again;
- verified findings;
- failed attempts that should not be repeated;
- blockers and the next action.

## Drop

- greetings and filler;
- repeated explanations;
- abandoned ideas that no longer affect the plan;
- large logs once the important lines are known;
- old implementation detail already captured in a file or commit.

## Method

1. Write the objective in one or two sentences.
2. Pull out non-negotiable constraints.
3. Record the current state as facts, not as a chronological story.
4. Keep assumptions separate from verified information.
5. Record decisions only with enough rationale to understand why they were made.
6. End with the next concrete action and how to check it.

Before finishing, imagine handing the compacted text to someone who cannot see the original conversation. If they would immediately need to ask what repository, branch, command, blocker, or decision you meant, the compaction removed too much.

Aim for a large reduction, but do not chase a fixed percentage. A 20-line incident can need more exact state than a 200-line brainstorming session.

See also: `handover`, `token-budget`, `context-router`.
