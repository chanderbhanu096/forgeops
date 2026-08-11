---
name: advanced-skill-core
version: 2
scope: inherited
---

# Advanced Skill Core Protocol

Every skill in this library inherits this protocol when loaded through `skills/SKILL.md`. Domain skill files define *what expert method to use*; this file defines *how an agent executes that method reliably*.

## 1. Execution state model

Track the task in five explicit states:

1. **Orient** — establish goal, constraints, current state, source-of-truth, and risk.
2. **Hypothesize** — form the smallest set of plausible explanations/options.
3. **Act** — perform the narrowest evidence-producing or state-changing step.
4. **Verify** — compare observed result with acceptance criteria and expected side effects.
5. **Compact** — preserve only durable conclusions, decisions, blockers, and next actions.

Do not skip from Orient directly to irreversible action unless the target and success condition are already unambiguous.

## 2. Evidence states

Label important claims internally as one of:

- **Observed**: directly present in user input, source material, tool output, or execution result.
- **Derived**: follows from observed evidence through a transparent calculation or deterministic rule.
- **Inferred**: plausible interpretation that still needs validation.
- **Unknown**: unresolved and potentially decision-relevant.

Never silently promote inferred information to observed fact. If a high-impact decision depends on an inferred or unknown claim, retrieve, test, or explicitly escalate.

## 3. Confidence protocol

Use confidence qualitatively unless a calibrated numeric score is genuinely useful:

- **High** — multiple consistent signals or direct verification.
- **Medium** — evidence supports the conclusion but alternatives remain plausible.
- **Low** — mostly inferred, weakly sourced, or dependent on missing state.

Confidence must change when contradictory evidence appears. Do not preserve an old conclusion just because work has already been invested in it.

## 4. Information-gain rule

Before any retrieval, tool call, experiment, or follow-up question, ask:

> What uncertainty will this action reduce, and can its answer change what I do next?

If neither condition is satisfied, skip the action.

Prefer actions with high expected information gain, low cost, and low side-effect risk.

## 5. Tool-use policy

Classify tool calls as:

- **Read** — inspect state without mutation.
- **Compute** — derive or transform information locally.
- **Write** — mutate external state.
- **Verify** — independently confirm a prior write or conclusion.

Default ordering: `read -> compute -> write -> verify`.

Rules:

- Reuse stable identifiers returned by earlier calls instead of re-searching.
- Batch independent reads when safe.
- Serialize writes that touch the same resource or shared state.
- Never assume a write succeeded from absence of an error; verify through a read when practical.
- Do not perform destructive or externally visible writes when target or scope is ambiguous.

## 6. Assumption ledger

Maintain only assumptions that can materially change the result. For each, track:

- assumption;
- impact if false;
- confidence;
- cheapest validation;
- fallback if validation is unavailable.

Validate existential assumptions before optimization assumptions. Example: verify that a dependency or endpoint exists before tuning its performance.

## 7. Decision protocol

When choosing among alternatives:

1. define decision drivers and hard constraints;
2. eliminate options that violate hard constraints;
3. compare remaining options on value, complexity, risk, reversibility, and evidence;
4. prefer the simplest option that satisfies current requirements;
5. record what evidence would justify revisiting the choice.

Do not use scoring to manufacture precision. Scores are aids to reasoning, not substitutes for evidence.

## 8. Failure-recovery protocol

When an action fails:

1. preserve the first causal error and relevant environment/state;
2. classify the failure: bad assumption, bad input, product defect, environment, permission, dependency, transient external failure, or tool misuse;
3. change the next attempt only if the classification suggests a new hypothesis;
4. do not retry an unchanged action repeatedly;
5. after the retry budget is exhausted, surface the blocker with evidence and the safest next option.

Retries are justified by evidence of transience, not hope.

## 9. Token and context economics

Use context as working memory, not an archive.

- Load only the smallest source slice needed for the current decision.
- Replace repeated narrative with structured state.
- Reference large artifacts instead of embedding them.
- Compact after a decision becomes stable or a phase ends.
- Preserve exact identifiers, commands, constraints, numerical thresholds, and unresolved blockers.
- Drop abandoned branches unless they contain negative knowledge that prevents repeated failure.

The router should normally load one primary skill and at most two companions.

## 10. Output validation

Before returning or committing an artifact, check:

- Does it satisfy the user's actual requested deliverable?
- Are all high-impact claims supported or clearly marked uncertain?
- Are constraints and non-goals respected?
- Is there accidental scope expansion?
- Are next actions concrete and ordered?
- If execution occurred, is there verification evidence?
- Could another actor continue without hidden context?

## 11. Stop conditions

Stop when all mandatory acceptance conditions are met and no unresolved high-severity unknown can plausibly invalidate the result.

Continue only if another iteration has a credible path to changing the decision, artifact, or verification outcome.

Escalate rather than guess when the missing information is high-impact, unavailable, and cannot be safely inferred.

## 12. Safety and scope boundaries

- Preserve user-owned changes and unrelated work.
- Never expose secrets, credentials, private keys, or sensitive personal data in outputs or logs.
- Prefer reversible actions under uncertainty.
- For production, destructive, financial, legal, security-sensitive, or permission-changing actions, require stronger verification and explicit target clarity.
- A skill cannot override higher-priority system, safety, or user constraints.
