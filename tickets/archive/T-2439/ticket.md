---
id: T-2439
title: Recovered from T-2403's phantom TICK006 citation of T-2407
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
Auto-filed by the TICK006 Tier-A fix (T-1544): T-2403's Done report claimed T-2407 was filed, but T-2407 resolves to no block in tickets.md or tickets-archive.md -- a phantom filing trail. The original claim's own surrounding text (the only surviving description of the intended work) is quoted verbatim below; review and refine as needed.

> first, then re-declared once it was the ONLY thing motivating
   the edge. Generalized into a new regression test (below).

### Remaining 8: filed as T-2407, not declared away

All 8 are "X -> cli" -- coupling into large, deeply CLI-integrated
modules (doctor.py 1249 lines, telemetry.py 1134, _daemo

## Drop reason
- 2026-08-18: false positive, same TICK006 stale-ledger-read race the coordinator is already tracking (T-2400 escalation, 3rd/4th occurrence today after T-2382/T-2383 and T-2398/T-2399): T-2407 is a real ticket, filed via frob ticket new moments before T-2403's land in the same session (verified: frob ticket show T-2407 resolves with real body content). Not a phantom citation.
