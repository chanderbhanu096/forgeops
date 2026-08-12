---
name: system-design
description: Turn requirements and workload assumptions into a design that can be built and operated.
---

# System design

Do not start with a diagram. Start with the workload and the promises the system needs to keep.

## Establish first

- who or what uses the system;
- main reads and writes;
- expected scale and traffic shape;
- latency and availability expectations;
- consistency requirements;
- data retention and privacy constraints;
- which failures are acceptable;
- what the team can realistically operate.

Then choose components.

## Work from the request path outward

Trace how a normal request enters, where state lives, which external systems are called, and what happens when each dependency is slow or unavailable.

Consider caching, queues, partitioning, replication, and asynchronous work only when a requirement creates the need. Do not add them because they are common in architecture diagrams.

Call out irreversible choices such as public APIs, data models, sharding keys, and cross-service ownership boundaries.

For important design decisions, include the simpler alternative and explain why it is not enough.

Finish with failure handling, observability, rollout, and the first capacity limit likely to be hit.

See also: `requirements-clarifier`, `architecture-tradeoffs`, `data-modeling`, `threat-model`.
