---
id: T-2054
title: 'post-land sweep regression from T-2030: 2 new (rule, file) identit(ies) (DUP001,
  SELFAUDIT001)'
state: queued
kind: bug
origin: agent
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- design
- tests/unit/test_land_orphaned_evidence_node_granularity.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
The deferred post-land unscoped sweep (T-1684) for T-2030 at commit 8d9598526f7f42d3191ea0ef163fb0c48a16ecc2 found 2 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES, not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). The true per-finding count could not be independently re-measured this run (spawn refused/timeout/unparsable) -- re-run `frob check` unscoped against the file(s) below for the exact count before treating this identity count as a completeness claim.

New (rule, file) identit(ies) filed here:

- DUP001  tests/unit/test_land_orphaned_evidence_node_granularity.py
- SELFAUDIT001  design

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.