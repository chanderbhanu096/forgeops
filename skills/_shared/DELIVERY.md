# Delivery and operations notes

Use these notes for security review, performance work, observability, documentation, releases, commits, and pull requests.

## Security

Look at trust boundaries and data flow before listing generic vulnerabilities.

For each meaningful risk, identify the asset, attacker or failure source, entry point, possible effect, and existing control. Prefer concrete abuse paths over checklist noise.

## Performance

Measure before optimizing when measurement is possible.

Separate latency, throughput, memory, CPU, I/O, and external-service time. A slow request can have very different fixes depending on which of those dominates.

## Observability

Logs and metrics are useful when they help answer an operational question.

Start from questions such as “which dependency is failing?”, “which requests are slow?”, or “did this release increase errors?” and add the smallest signal that answers them.

## Documentation

Document what the code actually does. Verify commands, defaults, paths, and examples against the current repository whenever possible.

Do not write feature marketing into setup instructions. If a limitation surprises a user, it probably belongs near the relevant instruction rather than at the bottom of the page.

## Releases

Before release, check the behavior being shipped, migrations, configuration changes, rollback path, and user-visible compatibility.

A green build is necessary but does not answer every release question.

## Commits and pull requests

A commit should contain one understandable change when practical. The message should say what changed, not advertise how important the change is.

A pull request should explain the problem, the chosen change, how it was checked, and anything reviewers need to pay special attention to.

Do not claim a test, migration, benchmark, or manual check was performed unless it actually was.
