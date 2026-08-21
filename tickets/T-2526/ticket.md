---
id: T-2526
title: 'post-land sweep regression from T-2503: 5 new (rule, file) identit(ies) (E501,
  F401, F811)'
state: done
kind: bug
origin: agent
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_app_runners_json_guard_t2492.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: scripts/fleet_status.py
  reason: split off to T-2531 -- different root cause (genuine long-line/unused-import
    findings) from this ticket's F811 lint false positive; narrowing so this ticket
    stays a clean single-file fix
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: src/frob/graph/summary.py
  reason: split off to T-2531 -- different root cause (genuine long-line/unused-import
    findings) from this ticket's F811 lint false positive; narrowing so this ticket
    stays a clean single-file fix
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: src/frob/testing/_collect_kotlin.py
  reason: split off to T-2531 -- different root cause (genuine long-line/unused-import
    findings) from this ticket's F811 lint false positive; narrowing so this ticket
    stays a clean single-file fix
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: tests/unit/test_ticket_runner_repro_merge_base.py
  reason: split off to T-2531 -- different root cause (genuine long-line/unused-import
    findings) from this ticket's F811 lint false positive; narrowing so this ticket
    stays a clean single-file fix
  actor: logan
  at: '2026-08-18'
body_changes:
- mode: append
  reason: BUG002 correctly refused confirmatory-only evidence since this bug-kind
    ticket's fix has no behavior to reproduce -- it silences a lint false positive,
    it does not change what any test does
  actor: logan
  at: '2026-08-18'
  old_length: 2328
  new_length: 2688
evidence:
- tests/unit/test_app_runners_json_guard_t2492.py::TestBindRunnerJsonGuard::test_planted_leak_does_not_reach_stdout
- tests/unit/test_app_runners_json_guard_t2492.py::TestGraphQueryRunnerJsonGuard::test_daemon_disabled_log_does_not_reach_stdout
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: b2c9e01ad5ab94de98329ad130495ad48b3d7af0
---
The deferred post-land unscoped sweep (T-1684) for T-2503 at commit a1c49a2a504e0730fbb1afaa0cb3ea83fcdb46b1 found 5 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES, not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). The true per-finding count could not be independently re-measured this run (spawn refused/timeout/unparsable) -- re-run `frob check` unscoped against the file(s) below for the exact count before treating this identity count as a completeness claim.

New (rule, file) identit(ies) filed here:

- E501  /home/logan/projects/frob/scripts/fleet_status.py
- E501  /home/logan/projects/frob/src/frob/graph/summary.py
- E501  /home/logan/projects/frob/src/frob/testing/_collect_kotlin.py
- F401  /home/logan/projects/frob/tests/unit/test_ticket_runner_repro_merge_base.py
- F811  /home/logan/projects/frob/tests/unit/test_app_runners_json_guard_t2492.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- E501  /home/logan/projects/frob/scripts/fleet_status.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- E501  /home/logan/projects/frob/src/frob/graph/summary.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- E501  /home/logan/projects/frob/src/frob/testing/_collect_kotlin.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- F401  /home/logan/projects/frob/tests/unit/test_ticket_runner_repro_merge_base.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- F811  /home/logan/projects/frob/tests/unit/test_app_runners_json_guard_t2492.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

<!-- frob:no-behavior-change reason="the fix is a lint-annotation-only change (six # noqa: F811 comments); no test/production code behavior changed, so no failing-at-parent/passing-at-fix pair exists for BUG002 to bind -- investigation in the Done report confirms all six flagged sites are the SAME correctly-imported fixture, not distinct redefinitions" -->