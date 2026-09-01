---
id: T-3622
title: 'ARCH103: split _leases.py mixed-concern helpers (_land_flock_probe, _live_pids_with_cwd)'
state: queued
kind: feature
origin: human
created: '2026-08-31'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_leases.py
- tests/**/*leases*
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
ARCH103 mixed-concern decomposition: src/frob/tickets/_leases.py's
_land_flock_probe and _live_pids_with_cwd each mix multiple concerns
in one function (per the self-gate refactor audit). Split each into
smaller, single-concern helpers. Keep externally observed behavior
identical -- this is a decomposition, not a behavior change.

Scope: src/frob/tickets/_leases.py + its test file.

Previously specified but never filed (LandInProgress starvation
during a prior agent's ~45 min of retries); refiled now as part of
draining that starved backlog.
