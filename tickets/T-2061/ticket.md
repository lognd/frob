---
id: T-2061
title: 'post-land sweep regression from T-2011: 2 new (rule, file) identit(ies), 23
  finding(s) (DUP001, SELFAUDIT001)'
state: dropped
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
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for T-2011 at commit bd12b4b9c3f67b7efcb7758d5f18d44cc9bc7684 found 2 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (2), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 23 actual finding(s) across those 2 identit(ies).

New (rule, file) identit(ies) filed here:

- DUP001  tests/unit/test_land_orphaned_evidence_node_granularity.py
- SELFAUDIT001  design

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- DUP001  tests/unit/test_land_orphaned_evidence_node_granularity.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- SELFAUDIT001  design  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-10: T-1983: auto-dropped by the deferred post-land sweep -- every (rule, file) identity this ticket named (DUP001 tests/unit/test_land_orphaned_evidence_node_granularity.py, SELFAUDIT001 design) is absent from the fresh unscoped measurement at doable's deferred sweep, i.e. no longer reproduces. If this is wrong (a flaky/incomplete measurement), re-file with `frob check --only <gate>` evidence attached.
