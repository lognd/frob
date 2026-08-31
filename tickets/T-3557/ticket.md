---
id: T-3557
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-3552):
  1 new (rule, file) identit(ies), 1 finding(s) (REG008)'
state: queued
kind: bug
origin: agent
created: '2026-08-31'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/design/registry/check-coverage.yaml
findings:
- - REG008
  - docs/design/registry/check-coverage.yaml
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
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-3552) at commit 7d590d79ae87c788c3d0f703421cc012c34d5f95 found 1 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (1), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 1 actual finding(s) across those 1 identit(ies).

New (rule, file) identit(ies) filed here:

- REG008  docs/design/registry/check-coverage.yaml

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- REG008  docs/design/registry/check-coverage.yaml  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Failure log
- 2026-08-31 attempt 1: Re-measured: 'uv run frob check --only registry' against this checkout's HEAD reports ZERO REG008 findings (registry=0.09s, no REG008 output). Root cause: commit 349ffd1b3 (T-3554, landed after this sweep's commit 7d590d79ae87c788c3d0f703421cc012c34d5f95) already fixed the exact gap this REG008 finding named -- 'fix(tickets): land T-3554 check-coverage registry missing entry for AUTOFIX001 (T-3526)'. This is pre-existing residue the rolling baseline had not recorded as fixed yet (T-1935/T-1690 lag between the sweep's frozen commit and a later, already-landed fix), not a live regression to fix here.
