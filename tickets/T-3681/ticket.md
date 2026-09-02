---
id: T-3681
title: 'self-gate floor: docs/modules/process.md DRIFT002 x3 + DRIFT001 ack (deferred
  from T-3674)'
state: queued
kind: bug
origin: human
created: '2026-09-01'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/process.md
- src/frob/process/_derived_lock.py
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
T-3674 (self-gate floor bucket a) fixed the DOC007/DRIFT002 pair in tests/test_tickets_leases.py but deferred:

- DRIFT002 x3 at docs/modules/process.md#public-api -> src/frob/process/_lock.py::{DerivedStateLockUnavailable,_derived_lock_path,derived_state_lock} no longer resolve (T-3628 moved these to _derived_lock.py) -- was leased by T-3673 (win32 round 17) at the time.
- DRIFT001 at src/frob/process/_derived_lock.py::_process_already_holds (digest moved since ack). frob ack on this symbol failed with UnknownRef ('not an edge endpoint') from a worktree -- independent of the lease, needs its own investigation (possibly the ack graph only resolves symbols reachable from a frob:doc-anchored edge, and this one's only anchor lives in the still-drifted doc).

Fix both together: repoint the process.md doc edges to _derived_lock.py, then re-attempt the ack.