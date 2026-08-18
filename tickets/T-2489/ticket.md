---
id: T-2489
title: 'post-land sweep regression from T-2411: 1 new (rule, file) identit(ies) (E501)'
state: done
kind: bug
origin: agent
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_waive_audit.py
evidence_scope:
- tests/integration/test_interfaces.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'BUG002 front door (T-2393): verified the sweep''s E501 identity no longer
    exists on main -- superseded by later lands (T-2485/T-2493) touching the same
    file; no code change needed'
  actor: logan
  at: '2026-08-18'
  old_length: 3754
  new_length: 3939
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 2eee0b464e2450301708f354a64c0c79eb8b90ef
---
The deferred post-land unscoped sweep (T-1684) for T-2411 at commit 918ec0c7d0675c95e5afa3a468fe3738c13dbc56 found 1 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES, not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). The true per-finding count could not be independently re-measured this run (spawn refused/timeout/unparsable) -- re-run `frob check` unscoped against the file(s) below for the exact count before treating this identity count as a completeness claim.

New (rule, file) identit(ies) filed here:

- E501  /home/logan/projects/frob/src/frob/app/ticket_runner/_waive_audit.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- E501  /home/logan/projects/frob/src/frob/app/ticket_runner/_waive_audit.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.