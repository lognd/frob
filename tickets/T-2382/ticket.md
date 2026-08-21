---
id: T-2382
title: Recovered from T-2341's phantom TICK006 citation of T-2367
state: dropped
kind: bug
origin: agent
created: '2026-08-17'
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
Auto-filed by the TICK006 Tier-A fix (T-1544): T-2341's Done report claimed T-2367 was filed, but T-2367 resolves to no block in tickets.md or tickets-archive.md -- a phantom filing trail. The original claim's own surrounding text (the only surviving description of the intended work) is quoted verbatim below; review and refine as needed.

> _coverage.py) -> T-2366. TICK004 (tickets.md
ledger-consistency, 9 errors + 17 warnings under one identity, needs
per-finding triage before a fix) -> T-2367.

STILL OPEN in this ticket's own (narrowed) scope, not attempted this
pass: SELFAUDIT001 (design, live but now 9 findings not 21 -- ratchet-
b

## Drop reason
- 2026-08-17: T-2367 is a real, filed ticket (frob ticket show T-2367 confirms queued state, real body); same TICK006 phantom-citation pattern T-2350 root-caused and T-2351 fixed (stale ledger read at land time). Not a genuine phantom.
