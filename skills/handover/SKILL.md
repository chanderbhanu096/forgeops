---
name: handover
description: Create a precise transfer packet that lets another agent, model, or human continue work without rediscovery.
---

# handover

## Mission

Move work across sessions or owners with minimal restart cost and no hidden state.

## Trigger conditions

- A session is ending or context may be reset.
- Ownership is moving to another model, agent, or person.
- A long-running task needs a recoverable checkpoint.

## Do not use when

- The next actor has full shared state and continuation is immediate.

## Inputs to establish

Before executing, establish only the inputs that materially affect the result:

- Goal and definition of done
- Work completed
- Current artifacts and locations
- Decisions and constraints
- Failures and lessons
- Next actions and verification commands

Do not ask the user for an input that can be safely inferred from supplied context or retrieved from an authoritative source. Mark inferred values as assumptions until verified.

## Operating protocol

1. Write the goal in operational terms, including what counts as finished.
2. List completed work as outcomes, not a chronological diary.
3. Capture exact artifact locations, branch/commit identifiers, commands, environment assumptions, and relevant credentials placeholders without secrets.
4. Record failed approaches and why they failed so the next actor does not repeat them.
5. State the current blocker or decision frontier, if any.
6. Provide the next 1-3 actions in order plus the command or evidence that proves each action succeeded.

## Advanced heuristics

- Optimize for restart time, not historical completeness.
- Distinguish “must preserve” from “nice to know.”
- Include negative knowledge: what was tried, rejected, or unsafe.
- If a handover cannot be acted on immediately, it is too vague.

## Failure modes to actively prevent

- Leaving out branch/commit or artifact locations.
- Saying “continue debugging” without the last observed failure.
- Copying large logs instead of extracting the decisive evidence.

## Evidence discipline

- Separate **observed**, **inferred**, and **unknown** information.
- Preserve provenance for claims that can change the decision.
- Prefer a discriminating test or authoritative source over additional speculation.
- If evidence contradicts the working theory, update the theory instead of rationalizing the evidence away.

## Output contract

Return the smallest useful artifact containing, as applicable:

- Mission
- State of work
- Artifacts/identifiers
- Decisions
- Known failures
- Blockers
- Next actions
- Verification

The output should be usable by the next actor without needing hidden reasoning or unstated context.

## Token and context discipline

Keep the packet small enough to paste into a new context; link or reference large artifacts rather than embedding them.

- Do not repeat source material unless exact wording is required.
- Keep large logs, documents, and code outside the active context; quote or load only decisive slices.
- Compact stable conclusions before opening a new exploration branch.

## Stop / escalate rules

Stop when the receiver can take the next action without asking what happened before.

Escalate instead of guessing when a missing fact is both high-impact and not safely inferable or retrievable. For write/destructive actions, stop if target or scope is ambiguous.

## Composition

Common companion skills: `context-compact`, `decision-record`, `execution-plan`

Load companions only for the phase where they add value; do not chain skills mechanically.
