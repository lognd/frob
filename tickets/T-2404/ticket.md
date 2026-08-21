---
id: T-2404
title: Recovered from T-2380's phantom TICK006 citation of T-2403
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
Auto-filed by the TICK006 Tier-A fix (T-1544): T-2380's Done report claimed T-2403 was filed, but T-2403 resolves to no block in tickets.md or tickets-archive.md -- a phantom filing trail. The original claim's own surrounding text (the only surviving description of the intended work) is quoted verbatim below; review and refine as needed.

> : `src/frob/app/graph_runner.py`
importing `frob.verify._selection` with no `cli -> verify` Flow, etc.) --
real work, not calibration noise. Filed as T-2403 (single-dispatch burn-
down + WARN->ERROR promotion), not split into multiple children: 133
spans ~45 distinct (from, to) pairs but is one cohe

## Drop reason
- 2026-08-18: false positive, same TICK006 stale-ledger-read race T-2350 already documented and confirmed dropped-mechanism-fixed post-T-2351: T-2403 is a real ticket, filed via frob ticket new moments before T-2380's land in the same session (verified: frob ticket show T-2403 resolves, state=queued). Not a phantom citation.
