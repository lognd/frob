---
id: T-2040
title: 'post-land sweep regression from T-2026: 2 new (rule, file) identit(ies), 2
  finding(s) (F401)'
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
- /home/logan/projects/frob/tests/test_gates_fmt_directives.py
- /home/logan/projects/frob/tests/unit/test_tickets_evidence_only_scope.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for T-2026 at commit 82bf70c5ca050fe701c372c7830d02aebab91012 found 2 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (2), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 2 actual finding(s) across those 2 identit(ies).

New (rule, file) identit(ies) filed here:

- F401  /home/logan/projects/frob/tests/test_gates_fmt_directives.py
- F401  /home/logan/projects/frob/tests/unit/test_tickets_evidence_only_scope.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- F401  /home/logan/projects/frob/tests/test_gates_fmt_directives.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- F401  /home/logan/projects/frob/tests/unit/test_tickets_evidence_only_scope.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-10: T-1983: auto-dropped by the deferred post-land sweep -- every (rule, file) identity this ticket named (F401 tests/test_gates_fmt_directives.py, F401 tests/unit/test_tickets_evidence_only_scope.py) is absent from the fresh unscoped measurement at T-1585's deferred sweep, i.e. no longer reproduces. If this is wrong (a flaky/incomplete measurement), re-file with `frob check --only <gate>` evidence attached.
