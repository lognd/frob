---
id: T-2038
title: 'post-land sweep regression from T-2034: 6 new (rule, file) identit(ies), 13
  finding(s) (ARCH001, ARCH103, DRIFT002, F401)'
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
- src/frob/app/ticket_runner/_query.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- tests/test_gates_fmt_directives.py
- tests/unit/test_tickets_evidence_only_scope.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
The deferred post-land unscoped sweep (T-1684) for T-2034 at commit d4a8eef02a6699dfd4224431d3b99d85de1bd81c found 6 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (6), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 13 actual finding(s) across those 6 identit(ies).

New (rule, file) identit(ies) filed here:

- ARCH001  src/frob/app/ticket_runner/_query.py
- ARCH001  src/frob/app/ticket_runner/_rapid_sweep.py
- ARCH103  src/frob/app/ticket_runner/_query.py
- DRIFT002  src/frob/app/ticket_runner/_rapid_sweep.py
- F401  tests/test_gates_fmt_directives.py
- F401  tests/unit/test_tickets_evidence_only_scope.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- ARCH001  src/frob/app/ticket_runner/_query.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH001  src/frob/app/ticket_runner/_rapid_sweep.py  -> attributed to T-2034 (commit 24c2622c4c0f, already closed/dropped -- filed below) via src/frob/app/ticket_runner/_rapid_sweep.py::_TICKET_DROP_COMMIT_MAX_ATTEMPTS
- ARCH103  src/frob/app/ticket_runner/_query.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DRIFT002  src/frob/app/ticket_runner/_rapid_sweep.py  -> attributed to T-2034 (commit 24c2622c4c0f, already closed/dropped -- filed below) via src/frob/app/ticket_runner/_rapid_sweep.py::_TICKET_DROP_COMMIT_MAX_ATTEMPTS
- F401  tests/test_gates_fmt_directives.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- F401  tests/unit/test_tickets_evidence_only_scope.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-10: T-1983: auto-dropped by the deferred post-land sweep -- every (rule, file) identity this ticket named (ARCH001 src/frob/app/ticket_runner/_query.py, ARCH001 src/frob/app/ticket_runner/_rapid_sweep.py, ARCH103 src/frob/app/ticket_runner/_query.py, DRIFT002 src/frob/app/ticket_runner/_rapid_sweep.py, F401 tests/test_gates_fmt_directives.py, F401 tests/unit/test_tickets_evidence_only_scope.py) is absent from the fresh unscoped measurement at T-1585's deferred sweep, i.e. no longer reproduces. If this is wrong (a flaky/incomplete measurement), re-file with `frob check --only <gate>` evidence attached.
