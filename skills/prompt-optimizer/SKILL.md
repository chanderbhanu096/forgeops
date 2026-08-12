---
name: prompt-optimizer
description: Clean up a prompt so the important behavior is clear and unnecessary instructions stop consuming context.
---

# Prompt optimizer

Use this when a prompt has grown through repeated edits, contains overlapping rules, or produces inconsistent behavior.

Do not optimize a prompt by making it sound more formal. Optimize it by removing ambiguity and repetition.

## Work through it in this order

1. Write down the actual task and expected output.
2. Separate hard rules from preferences.
3. Remove duplicate instructions, especially rules stated once positively and again negatively.
4. Move examples next to the rule they illustrate.
5. Resolve contradictions explicitly instead of relying on instruction order by accident.
6. Replace broad phrases such as “be accurate” with behavior that can be checked.
7. Keep tool rules close to the actions they govern.
8. Add a stop condition if the prompt tends to keep exploring after the job is done.

A sentence earns its place when removing it would change scope, behavior, tool use, evidence requirements, output format, or stopping behavior.

## Check the result

Try a normal case, a borderline case, and a case where the model should refuse or stop. If the rewritten prompt only works for the happy path, it is not finished.

Avoid giant collections of “never do X” rules when one positive instruction describes the intended behavior more clearly.

See also: `token-budget`, `context-router`, `stop-condition`.
