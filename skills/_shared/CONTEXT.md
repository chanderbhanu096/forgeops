# Context and prompt notes

Use these notes for context compaction, prompt cleanup, retrieval, handoff, and token budgeting.

The aim is not to make every prompt short. The aim is to stop paying context for information that no longer changes the work.

## What to keep

Keep these even when compressing aggressively:

1. hard constraints and safety boundaries;
2. the current objective and definition of done;
3. verified state and exact identifiers;
4. decisions that still affect the work;
5. failed approaches that should not be repeated;
6. unresolved assumptions with real impact;
7. the next action and how to check it.

## What to drop first

Usually safe to remove:

1. greetings and filler;
2. repeated statements;
3. superseded exploration;
4. examples that add no new constraint;
5. background that no longer affects a decision;
6. implementation details already stored in an artifact.

## Retrieve progressively

Do not open a large artifact just because it exists.

A useful order is:

```text
metadata -> search -> relevant excerpt -> nearby context -> full file if still needed
```

After each step, ask whether the question is already answered.

## Prompt cleanup

An instruction is worth keeping when removing it would change behavior, scope, evidence requirements, tool use, output format, or the stopping condition.

If removing a sentence would change none of those things, it is probably decoration.

## Handoff test

A handoff is good enough when someone new can answer these questions without opening the old conversation:

- What are we trying to finish?
- What has already been done?
- Where are the relevant files, branches, or artifacts?
- What failed?
- What must not change?
- What should happen next?
- How do we know the next step worked?
