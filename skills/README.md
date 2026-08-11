# Advanced General-Purpose LLM Skill Library

This directory contains **50 project-independent domain skills** plus a layered execution framework for Claude-style, Codex-style, Gemini-style, or custom tool-using agents.

The original version treated each `SKILL.md` as a standalone prompt fragment. Version 2 treats the library as a **capability graph with inherited execution protocols**. That makes the skills substantially more rigorous without copying the same reliability boilerplate into every file and wasting context tokens.

## Architecture

A skill invocation is composed from three layers:

```text
skills/SKILL.md                     router
        ↓
skills/_shared/CORE.md              universal execution discipline
        ↓
skills/_shared/<CATEGORY>.md        domain-family protocol
        ↓
skills/<skill-name>/SKILL.md        specialized method
```

The router should normally load **one primary skill** and **zero to two companions**.

## What the shared core adds

Every routed skill inherits:

- explicit Orient → Hypothesize → Act → Verify → Compact state transitions;
- observed / derived / inferred / unknown evidence states;
- confidence handling and contradiction rules;
- information-gain checks before retrieval or tool calls;
- read / compute / write / verify tool sequencing;
- an assumption ledger for high-impact uncertainty;
- reversible-decision heuristics;
- failure classification and bounded retry behavior;
- token/context economics;
- output validation;
- stop and escalation conditions;
- safety and external-write boundaries.

## Category protocols

`_shared/CONTEXT.md` handles compression, retrieval economics, prompt density, and handoff quality.

`_shared/THINKING.md` handles divergence/convergence, problem framing, planning boundaries, reversibility, and risk quality.

`_shared/RESEARCH.md` handles claim-first research, source weighting, contradictions, structured extraction, and experiment discipline.

`_shared/ENGINEERING.md` handles codebase orientation, debugging loops, invariants, test economics, refactoring, and review severity.

`_shared/DELIVERY.md` handles security, performance, observability, documentation correctness, release gates, and Git delivery.

## Skill groups

### Context and token efficiency

`context-compact`, `handover`, `prompt-optimizer`, `context-router`, `token-budget`, `response-compressor`, `progressive-disclosure`, `retrieval-first`, `tool-call-planner`, `stop-condition`

### Thinking and planning

`brainstorm`, `idea-evaluator`, `problem-framing`, `requirements-clarifier`, `task-decomposer`, `execution-plan`, `project-kickoff`, `decision-record`, `assumption-audit`, `risk-register`

### Research and knowledge

`research-plan`, `source-synthesizer`, `fact-check`, `summarizer`, `structured-extractor`, `experiment-design`, `retrospective`, `learning-mode`

### Engineering and architecture

`codebase-orient`, `debug`, `root-cause-analysis`, `minimal-fix`, `refactor-safely`, `code-review`, `test-strategy`, `test-failure-triage`, `ci-debug`, `dependency-audit`, `api-design`, `system-design`, `architecture-tradeoffs`, `data-modeling`

### Quality, security, operations, and delivery

`security-review`, `threat-model`, `performance-analysis`, `observability-plan`, `documentation-writer`, `release-readiness`, `git-commit`, `pull-request`

## Skill maturity standard

A mature domain skill should define:

1. a narrow mission;
2. trigger and anti-trigger conditions;
3. minimum inputs;
4. a repeatable operating protocol;
5. domain heuristics that change decisions;
6. known failure modes;
7. an output contract;
8. token/context discipline where domain-specific;
9. stop/escalation rules;
10. useful composition edges to other skills.

Shared execution behavior belongs in `_shared/` instead of being duplicated everywhere.

## Design principle

**Sophistication should increase decision quality, not prompt length.**

A long skill that repeats generic instructions is worse than a concise domain skill composed with a strong inherited protocol. The library is optimized for selective loading, phase transitions, and low context duplication.
