---
name: context-efficiency-protocol
scope: category
---

# Context & Token Efficiency Protocol

Applies to: `context-compact`, `handover`, `prompt-optimizer`, `context-router`, `token-budget`, `response-compressor`, `progressive-disclosure`, `retrieval-first`, `tool-call-planner`, `stop-condition`.

## Objective

Maximize useful work per context token while preserving correctness-critical state.

## Compression hierarchy

Discard in this order:

1. pleasantries and conversational filler;
2. exact repetition;
3. superseded intermediate reasoning;
4. examples that add no unique constraint or evidence;
5. low-impact background;
6. implementation detail already captured in an artifact.

Preserve in this order:

1. hard constraints and safety boundaries;
2. current objective and acceptance criteria;
3. verified state and exact identifiers;
4. decisions and reversal triggers;
5. failures and negative knowledge;
6. unresolved high-impact assumptions;
7. next actions and verification commands.

## Context pressure signals

Trigger compaction when any of these appear:

- the same facts are restated across multiple turns;
- the agent repeatedly re-reads the same artifact;
- old exploration branches dominate active context;
- tool outputs are much larger than the decisive evidence they contain;
- the next phase no longer needs detailed history from the previous phase.

## Retrieval economics

Use progressive retrieval:

`metadata -> targeted search -> narrow excerpt -> adjacent context -> full artifact only if still necessary`.

After every retrieval, ask whether the evidence threshold is already met.

## Prompt density test

A prompt instruction earns its tokens only if removing it would alter at least one of:

- behavior;
- scope;
- evidence standard;
- tool policy;
- output format;
- stopping condition.

Otherwise delete it.

## Handoff quality test

A handoff passes only if a new agent can answer without the original conversation:

- What are we trying to accomplish?
- What is already done?
- What exact state/artifacts exist?
- What failed and why?
- What must not change?
- What is the next safe action?
- How will success be verified?
