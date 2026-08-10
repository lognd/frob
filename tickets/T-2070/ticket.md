---
id: T-2070
title: 'post-land sweep regression from T-1959, T-2003, T-2016: 3 new (rule, file)
  identit(ies), 2 finding(s) (COV001, DOC002, DSL001)'
state: done
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
- src/frob/strata/_claims.py
- docs/strata/kernel.md
evidence_scope:
- tests/integration/test_interfaces.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/strata/kernel.md
  reason: DOC002 fix requires writing the missing claim-evaluation section this ticket's
    frob:doc anchor points at
  actor: logan
  at: '2026-08-10'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
The deferred post-land unscoped sweep (T-1684) for T-1959, T-2003, T-2016 at commit 093254241378b66abf0d434bb21760da596be2b4 found 3 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (3), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 2 actual finding(s) across those 3 identit(ies).

New (rule, file) identit(ies) filed here:

- COV001  src/frob/strata/_claims.py
- DOC002  src/frob/strata/_claims.py
- DSL001  src/frob/app/ticket_runner/_query.py

T-2009: 3 lands (T-1959, T-2003, T-2016) landed between the previous sweep's baseline and the commit THIS sweep actually measured (the sweep is deliberately detached, off the land critical path -- T-1684 -- so other agents' lands can land in the window before it runs). Which specific land introduced which finding below could not be determined without re-measuring at each intermediate commit; this ticket is filed against all of them rather than falsely pinned on T-1959 alone (the one that happened to spawn this sweep process).

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- COV001  src/frob/strata/_claims.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC002  src/frob/strata/_claims.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DSL001  src/frob/app/ticket_runner/_query.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.