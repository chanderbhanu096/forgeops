---
name: skill-router
description: Route a task to the smallest sufficient combination of a domain skill and inherited advanced execution protocols.
version: 2
---

# Skill Router

## Purpose

This file is the entry point for the skill library. The library is deliberately layered so sophistication does not require duplicating the same reliability rules across 50 files.

A loaded skill is interpreted as:

`advanced core protocol + category protocol + primary domain skill (+ optional companion skills)`

## Mandatory inheritance

When any skill under `skills/*/SKILL.md` is invoked through this router:

1. Apply `skills/_shared/CORE.md`.
2. Apply the category protocol that contains the skill.
3. Load the skill's own `SKILL.md` for domain-specific method.
4. Load at most two companion skills only when they address a separate risk or phase.

The shared protocol is inherited behavior. It does not need to be copied into every skill file.

## Category mapping

### Context and token efficiency

Protocol: `skills/_shared/CONTEXT.md`

Skills: `context-compact`, `handover`, `prompt-optimizer`, `context-router`, `token-budget`, `response-compressor`, `progressive-disclosure`, `retrieval-first`, `tool-call-planner`, `stop-condition`.

### Thinking and planning

Protocol: `skills/_shared/THINKING.md`

Skills: `brainstorm`, `idea-evaluator`, `problem-framing`, `requirements-clarifier`, `task-decomposer`, `execution-plan`, `project-kickoff`, `decision-record`, `assumption-audit`, `risk-register`.

### Research and knowledge

Protocol: `skills/_shared/RESEARCH.md`

Skills: `research-plan`, `source-synthesizer`, `fact-check`, `summarizer`, `structured-extractor`, `experiment-design`, `retrospective`, `learning-mode`.

### Engineering and architecture

Protocol: `skills/_shared/ENGINEERING.md`

Skills: `codebase-orient`, `debug`, `root-cause-analysis`, `minimal-fix`, `refactor-safely`, `code-review`, `test-strategy`, `test-failure-triage`, `ci-debug`, `dependency-audit`, `api-design`, `system-design`, `architecture-tradeoffs`, `data-modeling`.

### Quality, security, operations, and delivery

Protocol: `skills/_shared/DELIVERY.md`

Skills: `security-review`, `threat-model`, `performance-analysis`, `observability-plan`, `documentation-writer`, `release-readiness`, `git-commit`, `pull-request`.

## Routing algorithm

### Step 1: classify the active phase

Choose exactly one primary phase:

- **understand** — clarify, orient, frame, or retrieve;
- **explore** — brainstorm, compare, or discover options;
- **decide** — evaluate alternatives or record a decision;
- **plan** — decompose, sequence, or assess risk;
- **implement** — change code, data, prompts, or artifacts;
- **verify** — test, review, fact-check, or measure;
- **deliver** — document, commit, release, or open a PR;
- **handoff** — compact and transfer state.

### Step 2: choose one primary skill

Pick the skill whose output contract most directly matches the user's requested deliverable.

Do not choose a skill merely because it is adjacent to the topic.

### Step 3: decide whether companions are needed

A companion skill is justified only if it handles one of:

- a distinct high-risk boundary;
- an independent evidence problem;
- a required transition into the next phase.

Default maximum: two companions.

### Step 4: execute until the primary skill stops

Use the primary skill's stop condition plus the inherited stop rules in `CORE.md`.

Do not mechanically continue through a pre-written chain if the user's requested artifact is already complete.

### Step 5: re-route on phase transition

Once a phase is complete, compact durable state and choose a new primary skill only if more work is genuinely required.

## Canonical routes

- Ambiguous request: `problem-framing -> requirements-clarifier -> task-decomposer`
- New product/project idea: `brainstorm -> idea-evaluator -> experiment-design`
- Research question: `research-plan -> retrieval-first -> source-synthesizer -> fact-check`
- Bug: `codebase-orient -> debug -> minimal-fix -> test-strategy`
- Incident: `debug -> root-cause-analysis -> observability-plan -> retrospective`
- Refactor: `codebase-orient -> refactor-safely -> test-strategy -> code-review`
- New API: `requirements-clarifier -> api-design -> threat-model -> test-strategy`
- New system: `requirements-clarifier -> system-design -> architecture-tradeoffs -> threat-model`
- Performance issue: `performance-analysis -> observability-plan -> experiment-design`
- Release: `code-review -> security-review -> release-readiness -> git-commit -> pull-request`
- Context pressure: `token-budget -> context-compact`; add `handover` only at an ownership/session boundary.

## Anti-patterns

Do not:

- load all 50 skills;
- use more skills as a substitute for clearer problem framing;
- re-run a skill whose output contract is already satisfied;
- carry detailed exploration history into delivery phases;
- load engineering/security protocols for unrelated writing or ideation tasks;
- use a companion merely because another skill references it.

## Router output

When explicit routing output is useful, return only:

- primary skill;
- inherited category protocol;
- optional companions;
- why each is needed;
- stop condition for the current phase.

Normally this routing remains implicit and the agent proceeds directly to useful work.
