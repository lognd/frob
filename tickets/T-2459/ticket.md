---
id: T-2459
title: Recovered from T-2394's phantom TICK006 citation of T-draft-b08172a8
state: dropped
kind: bug
origin: agent
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Auto-filed by the TICK006 Tier-A fix (T-1544): T-2394's Done report claimed T-draft-b08172a8 was filed, but T-draft-b08172a8 resolves to no block in tickets.md or tickets-archive.md -- a phantom filing trail. The original claim's own surrounding text (the only surviving description of the intended work) is quoted verbatim below; review and refine as needed.

> esting requeue/close/archive/land dispatch). Fixed by
giving each a real one-file scope; re-ran the touched set clean
afterward. Also found and filed T-draft-b08172a8 (out of scope: the
related-title duplicate detector false-positiving "holder"/"collider" at
71%, breaking a pre-existing TestTicketSt

## Drop reason
- 2026-08-18: stale recovery artifact -- both T-2459 and T-2461 recovered identical text from T-2394's phantom TICK006 citation of T-draft-b08172a8; the quoted defect (related-title duplicate detector false-positiving holder/collider at 71%, breaking a pre-existing TestTicketStart test) is exactly T-2455, filed and landed independently at commit 525baabf2412a68f2499fbccb3dc241a41f7688e. No remaining work. (absorbed by T-2455)
