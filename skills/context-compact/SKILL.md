---
name: context-compact
description: Compress large working context into a loss-minimized continuation state for another model turn or agent.
---

# context-compact

## Mission

Reduce context cost while preserving every fact that can change future decisions or execution.

## Trigger conditions

- Conversation or task history is long enough that repetition is consuming context.
- A handoff, checkpoint, or model switch is approaching.
- The agent needs a stable state snapshot before a risky or multi-step phase.

## Do not use when

- The source context is already short and active details are still changing rapidly.
- The user explicitly needs a verbatim transcript rather than a working-state summary.

## Inputs to establish

Before executing, establish only the inputs that materially affect the result:

- Current objective and success criteria
- Hard constraints and user preferences
- Decisions already made and their rationale
- Verified evidence, identifiers, paths, commands, numbers, and URLs
- Open questions, blockers, failed attempts, and next actions

Do not ask the user for an input that can be safely inferred from supplied context or retrieved from an authoritative source. Mark inferred values as assumptions until verified.

## Operating protocol

1. Partition context into invariant facts, decisions, evidence, active work, and disposable history.
2. Promote exact values that future execution depends on; never paraphrase identifiers, commands, paths, version numbers, or thresholds.
3. Collapse repeated discussion into the latest settled decision and record superseded choices only when reversal risk exists.
4. Separate verified facts from assumptions and unresolved hypotheses.
5. Encode current execution state: what is done, what is in progress, what failed, and the next smallest safe action.
6. Run a loss audit: ask whether a fresh agent could continue correctly using only the compacted state.

## Advanced heuristics

- Use delta compression: preserve what changed since the previous checkpoint instead of re-summarizing everything.
- Keep rationale only for decisions likely to be questioned or reversed.
- Represent lists and state machines structurally; use prose only for nuance.
- Prefer one canonical statement of each fact to multiple paraphrases.

## Failure modes to actively prevent

- Deleting a constraint because it appeared only once.
- Mixing guesses with verified state.
- Producing a narrative summary that is pleasant to read but unusable for continuation.

## Evidence discipline

- Separate **observed**, **inferred**, and **unknown** information.
- Preserve provenance for claims that can change the decision.
- Prefer a discriminating test or authoritative source over additional speculation.
- If evidence contradicts the working theory, update the theory instead of rationalizing the evidence away.

## Output contract

Return the smallest useful artifact containing, as applicable:

- Objective
- Non-negotiable constraints
- Current verified state
- Decisions and rationale
- Open risks/blockers
- Next actions
- Discarded/superseded context worth remembering

The output should be usable by the next actor without needing hidden reasoning or unstated context.

## Token and context discipline

Target 10-25% of the source context. Expand only when compression would create ambiguity or erase an execution-critical detail.

- Do not repeat source material unless exact wording is required.
- Keep large logs, documents, and code outside the active context; quote or load only decisive slices.
- Compact stable conclusions before opening a new exploration branch.

## Stop / escalate rules

Stop when a fresh agent can state the goal, constraints, current state, and next action without consulting the original context.

Escalate instead of guessing when a missing fact is both high-impact and not safely inferable or retrievable. For write/destructive actions, stop if target or scope is ambiguous.

## Composition

Common companion skills: `handover`, `token-budget`, `context-router`

Load companions only for the phase where they add value; do not chain skills mechanically.
