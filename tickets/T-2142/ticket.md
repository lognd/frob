---
id: T-2142
title: 'post-land sweep regression from T-1996: 1 new (rule, file) identit(ies) (E402)'
state: dropped
kind: bug
origin: agent
created: '2026-08-11'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/test_ticket_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for T-1996 at commit d703ea2f5c447997c9fdd837a2d920b032ad5e3f found 1 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES, not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). The true per-finding count could not be independently re-measured this run (spawn refused/timeout/unparsable) -- re-run `frob check` unscoped against the file(s) below for the exact count before treating this identity count as a completeness claim.

New (rule, file) identit(ies) filed here:

- E402  tests/test_ticket_leases.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- E402  tests/test_ticket_leases.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-16: T-1983: auto-dropped by the deferred post-land sweep -- every (rule, file) identity this ticket named (E402 tests/test_ticket_leases.py) is absent from the fresh unscoped measurement at doable's deferred sweep, i.e. no longer reproduces. If this is wrong (a flaky/incomplete measurement), re-file with `frob check --only <gate>` evidence attached.
