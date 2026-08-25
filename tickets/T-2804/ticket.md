---
id: T-2804
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-2796):
  3 new (rule, file) identit(ies), 3 finding(s) (DOC001, DOC011, TICK006)'
state: done
kind: bug
origin: agent
created: '2026-08-21'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/investigations/T-2796-backlog-reproduction.md
- tickets.md
findings:
- - DOC001
  - docs/investigations/T-2796-backlog-reproduction.md
- - DOC011
  - docs/investigations/T-2796-backlog-reproduction.md
- - TICK006
  - tickets.md
evidence_scope:
- tests/integration/test_interfaces.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'BUG002 waiver: ledger correction, not a reproducible code defect'
  actor: logan
  at: '2026-08-25'
  old_length: 1080
  new_length: 1405
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: e30c790edecc28b7cdff500050180fc1eceb65c5
---
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-2796) at commit 514041b50387f289b8687b6eb873308ae5516d0a found 3 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (3), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 3 actual finding(s) across those 3 identit(ies).

New (rule, file) identit(ies) filed here:

- DOC001  docs/investigations/T-2796-backlog-reproduction.md
- DOC011  docs/investigations/T-2796-backlog-reproduction.md
- TICK006  tickets.md

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.


<!-- frob:waive BUG002 reason="ledger/doc correction (a phantom-filing-claim fix in an archived Done report), not a code defect -- there is no caller/wiring path to reproduce with a mutation-killing test; the existing CLI-dispatch integration test is recorded as evidence per playbook section 5's docs-only precedent" -->