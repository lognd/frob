---
id: T-2383
title: Recovered from T-2341's phantom TICK006 citation of T-2366
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
Auto-filed by the TICK006 Tier-A fix (T-1544): T-2341's Done report claimed T-2366 was filed, but T-2366 resolves to no block in tickets.md or tickets-archive.md -- a phantom filing trail. The original claim's own surrounding text (the only surviving description of the intended work) is quoted verbatim below; review and refine as needed.

> patches, children filed): COV003 x4 (T-1205/
T-1235/T-1397/T-1526's bound evidence does not resolve against tests/
unit/test_makefile_coverage.py) -> T-2366. TICK004 (tickets.md
ledger-consistency, 9 errors + 17 warnings under one identity, needs
per-finding triage before a fix) -> T-2367.

STILL OP

## Drop reason
- 2026-08-17: T-2366 is a real, filed ticket (frob ticket show T-2366 confirms queued state, real body); same TICK006 phantom-citation pattern T-2350 root-caused and T-2351 fixed. Not a genuine phantom.
