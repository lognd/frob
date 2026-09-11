---
id: T-4394
title: 'post-land sweep regression from T-4388: 4 new (rule, file) identit(ies), 15
  finding(s) (DRIFT001, REG005, TICK004, TICK006)'
state: done
kind: docs
origin: agent
created: '2026-09-10'
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
- src/frob/tickets/_leases.py
- tickets.md
- docs/modules/tickets-lifecycle.md
findings:
- - DRIFT001
  - src/frob/tickets/_leases.py
- - REG005
  - docs/design/registry/check-coverage.yaml
- - TICK004
  - tickets.md
- - TICK006
  - tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets-lifecycle.md
  reason: DRIFT001's finding is anchored on src/frob/tickets/_leases.py but the acked
    doc section it points at lives in docs/modules/tickets-lifecycle.md; fixing the
    actual drift requires editing that file
  actor: logan
  at: '2026-09-10'
triage_changes:
- field: kind
  old_value: bug
  new_value: docs
  reason: registry row count plus a doc ack; no diff-touched code exists for mutation
    evidence (mirrors the kind change on main, 715c75f9e)
  actor: logan
  at: '2026-09-10'
body_changes:
- mode: append
  reason: 'T-4394 Done report: REG005/DRIFT001 fixed, TICK004/TICK006 confirmed pre-existing
    residue'
  actor: logan
  at: '2026-09-10'
  old_length: 2285
  new_length: 6713
- mode: set
  reason: revert accidental bold Done-report note from body; the real Done report
    now lives correctly in tickets/T-4394/done-report.md via set_done_report
  actor: logan
  at: '2026-09-10'
  old_length: 6712
  new_length: 2286
evidence:
- tests/test_registry_exhaustiveness.py::TestTotalDrift::test_total_mismatch_fails
- tests/test_graph_lock.py::TestAckDrift::test_ack_then_sig_edit_yields_stale
kind_history:
- 2026-09-10 bug->docs evidence=2 done_report=yes
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for T-4388 at commit 90ecadfa1b737d7cc7ac4601cb7bfab2bc2b9905 found 7 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (4), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 15 actual finding(s) across those 4 identit(ies).

New (rule, file) identit(ies) filed here:

- DRIFT001  src/frob/tickets/_leases.py
- REG005  docs/design/registry/check-coverage.yaml
- TICK004  tickets.md
- TICK006  tickets.md

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- DRIFT001  src/frob/tickets/_leases.py  -> attributed to T-4388 (commit 90ecadfa1b73, already closed/dropped -- filed below) via src/frob/app/ticket_runner/_archive.py::_require_reason_for_archive_force -> src/frob/app/ticket_runner/_archive.py::_record_or_refuse_archive_force -> src/frob/tickets/_leases.py::_LeaseRecord
- LARGE001  src/frob/app/verify_runner.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- LARGE001  src/frob/testing/_collect.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- LARGE001  src/frob/tickets/_archive.py  -> attributed to T-4388 (commit 90ecadfa1b73, already closed/dropped -- filed below) via src/frob/tickets/_archive.py::_refuse_archive_if_leased
- REG005  docs/design/registry/check-coverage.yaml  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK004  tickets.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK006  tickets.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.