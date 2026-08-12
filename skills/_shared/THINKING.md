# Planning and decision notes

Use these notes for brainstorming, requirements, planning, assumptions, and trade-offs.

## Separate exploration from selection

When the solution is not known yet, generate genuinely different options first. Do not make ten variations of the same idea and call that breadth.

Once there are enough options, switch modes and compare them using the constraints that actually matter.

## Frame the problem before optimizing it

Write down the decision, the affected user or system, the constraints, and the evidence that would change the answer.

A good problem statement is usually narrower than the first request. Avoid solving adjacent problems unless they are required for the main one.

## Requirements

Separate:

- must-have behavior;
- useful behavior;
- explicit non-goals;
- assumptions;
- open questions.

Do not turn every preference into a hard requirement.

## Trade-offs

Compare options using concrete costs such as complexity, latency, reliability, maintenance, security, migration effort, and reversibility.

A choice that is easy to reverse does not need the same amount of analysis as a public API or data model that will be expensive to change later.

## Risks

A useful risk describes an event, why it could happen, the effect, and what can be done about it.

“Performance may be bad” is weak. “The synchronous enrichment call is on the request path and can add the upstream API's p99 latency to every request” is useful.

## Plans

Plans should expose checkpoints and verification, not just a long list of tasks.

Prefer small steps where the result of one step changes what should happen next.
