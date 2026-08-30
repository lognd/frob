---
id: T-3286
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-3272):
  2 new (rule, file) identit(ies) (unknown-argument)'
state: queued
kind: bug
origin: agent
created: '2026-08-28'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_app_runners_process.py
- tests/unit/test_pytest_spawn_env_wiring.py
findings:
- - unknown-argument
  - tests/unit/test_app_runners_process.py
- - unknown-argument
  - tests/unit/test_pytest_spawn_env_wiring.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 65f4dec52e3713599c04e412b01ce9ca3846a67e
---
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-3272) at commit 8ac6892fd9eff7cd389a3913f64b63e4d5410438 found 2 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES, not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). The true per-finding count could not be independently re-measured this run (spawn refused/timeout/unparsable) -- re-run `frob check` unscoped against the file(s) below for the exact count before treating this identity count as a completeness claim.

New (rule, file) identit(ies) filed here:

- unknown-argument  tests/unit/test_app_runners_process.py
- unknown-argument  tests/unit/test_pytest_spawn_env_wiring.py

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Failure log
- 2026-08-29 attempt 1: already resolved on main, not reproducible -- see Failure log for measured evidence
