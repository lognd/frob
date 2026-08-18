---
id: T-2439
title: Recovered from T-2403's phantom TICK006 citation of T-2407
state: queued
kind: bug
origin: agent
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Auto-filed by the TICK006 Tier-A fix (T-1544): T-2403's Done report claimed T-2407 was filed, but T-2407 resolves to no block in tickets.md or tickets-archive.md -- a phantom filing trail. The original claim's own surrounding text (the only surviving description of the intended work) is quoted verbatim below; review and refine as needed.

> first, then re-declared once it was the ONLY thing motivating
   the edge. Generalized into a new regression test (below).

### Remaining 8: filed as T-2407, not declared away

All 8 are "X -> cli" -- coupling into large, deeply CLI-integrated
modules (doctor.py 1249 lines, telemetry.py 1134, _daemo