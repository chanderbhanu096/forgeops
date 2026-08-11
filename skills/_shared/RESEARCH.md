---
name: research-knowledge-protocol
scope: category
---

# Research & Knowledge Protocol

Applies to: `research-plan`, `source-synthesizer`, `fact-check`, `summarizer`, `structured-extractor`, `experiment-design`, `retrospective`, `learning-mode`.

## Objective

Produce decision-quality knowledge with traceable evidence, bounded uncertainty, and minimal retrieval waste.

## Claim-first research

Break the question into claims or subquestions before searching. For each claim, define the strongest plausible source type and the evidence threshold required to act.

Search for the unknown, not the whole topic.

## Source weighting

Evaluate evidence on:

- authority;
- directness;
- methodology;
- recency where relevant;
- scope match;
- independence from other sources.

Do not count multiple sources as independent corroboration when they repeat the same upstream claim.

## Contradiction handling

When sources disagree:

1. check whether they use different definitions, populations, versions, or time windows;
2. prefer primary evidence for exact factual questions;
3. preserve meaningful disagreement rather than averaging it away;
4. state what additional evidence would resolve the dispute.

## Extraction discipline

For structured extraction:

- define schema first;
- distinguish missing from unknown from not-applicable;
- normalize units and dates explicitly;
- preserve raw source value when normalization can lose meaning;
- retain provenance at field or record level for consequential data.

## Experiment discipline

An experiment must define before execution:

- hypothesis;
- decision it informs;
- baseline/control;
- intervention;
- primary metric;
- guardrail metrics;
- minimum meaningful effect;
- analysis method;
- stopping criteria;
- response to positive, negative, and inconclusive outcomes.

If no plausible result would change a decision, do not run the experiment.
