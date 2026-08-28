---
id: T-3219
title: 'post-land sweep regression from T-3195: 23 new (rule, file) identit(ies) (COV003,
  DOC007, DRIFT002, REF002)'
state: queued
kind: bug
origin: agent
created: '2026-08-28'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- scripts/fleet_status.py
- src/frob/check/_python.py
- src/frob/tickets/_done_report.py
- tests/system/test_fleet_status_ground_truth.py
- tests/test_app_daemon_proxy.py
- tests/test_coverage_wait_shared.py
- tests/test_serve_leases.py
- tests/test_serve_socket.py
- tests/test_ticket_land.py
- tests/test_ticket_leases.py
- tests/test_ticket_reconcile.py
- tests/test_tickets_parent.py
- tests/test_tickets_priority.py
- tests/unit/test_conftest_stackdump.py
- tests/unit/test_coordinator_scripts.py
- tests/unit/test_land_finish_guard.py
- tests/unit/test_land_lock_liveness.py
- tests/unit/test_process_lock.py
- tests/unit/test_rapid_sweep.py
- tests/unit/test_stackdump.py
- tests/unit/test_ticket_store.py
- tickets/T-3181
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
findings:
- - COV003
  - tickets/T-3181
- - DOC007
  - src/frob/check/_python.py
- - DRIFT002
  - src/frob/check/_python.py
- - REF002
  - src/frob/tickets/_done_report.py
- - unresolved-attribute
  - scripts/fleet_status.py
- - unresolved-attribute
  - tests/system/test_fleet_status_ground_truth.py
- - unresolved-attribute
  - tests/test_app_daemon_proxy.py
- - unresolved-attribute
  - tests/test_coverage_wait_shared.py
- - unresolved-attribute
  - tests/test_serve_leases.py
- - unresolved-attribute
  - tests/test_serve_socket.py
- - unresolved-attribute
  - tests/test_ticket_land.py
- - unresolved-attribute
  - tests/test_ticket_leases.py
- - unresolved-attribute
  - tests/test_ticket_reconcile.py
- - unresolved-attribute
  - tests/test_tickets_parent.py
- - unresolved-attribute
  - tests/test_tickets_priority.py
- - unresolved-attribute
  - tests/unit/test_conftest_stackdump.py
- - unresolved-attribute
  - tests/unit/test_coordinator_scripts.py
- - unresolved-attribute
  - tests/unit/test_land_finish_guard.py
- - unresolved-attribute
  - tests/unit/test_land_lock_liveness.py
- - unresolved-attribute
  - tests/unit/test_process_lock.py
- - unresolved-attribute
  - tests/unit/test_rapid_sweep.py
- - unresolved-attribute
  - tests/unit/test_stackdump.py
- - unresolved-attribute
  - tests/unit/test_ticket_store.py
---
The deferred post-land unscoped sweep (T-1684) for T-3195 at commit 46b172704c7008408feedb7624654e233336eae9 found 23 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES, not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). The true per-finding count could not be independently re-measured this run (spawn refused/timeout/unparsable) -- re-run `frob check` unscoped against the file(s) below for the exact count before treating this identity count as a completeness claim.

New (rule, file) identit(ies) filed here:

- COV003  tickets/T-3181
- DOC007  src/frob/check/_python.py
- DRIFT002  src/frob/check/_python.py
- REF002  src/frob/tickets/_done_report.py
- unresolved-attribute  scripts/fleet_status.py
- unresolved-attribute  tests/system/test_fleet_status_ground_truth.py
- unresolved-attribute  tests/test_app_daemon_proxy.py
- unresolved-attribute  tests/test_coverage_wait_shared.py
- unresolved-attribute  tests/test_serve_leases.py
- unresolved-attribute  tests/test_serve_socket.py
- unresolved-attribute  tests/test_ticket_land.py
- unresolved-attribute  tests/test_ticket_leases.py
- unresolved-attribute  tests/test_ticket_reconcile.py
- unresolved-attribute  tests/test_tickets_parent.py
- unresolved-attribute  tests/test_tickets_priority.py
- unresolved-attribute  tests/unit/test_conftest_stackdump.py
- unresolved-attribute  tests/unit/test_coordinator_scripts.py
- unresolved-attribute  tests/unit/test_land_finish_guard.py
- unresolved-attribute  tests/unit/test_land_lock_liveness.py
- unresolved-attribute  tests/unit/test_process_lock.py
- unresolved-attribute  tests/unit/test_rapid_sweep.py
- unresolved-attribute  tests/unit/test_stackdump.py
- unresolved-attribute  tests/unit/test_ticket_store.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- COV003  tickets/T-3181  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC007  src/frob/check/_python.py  -> attributed to T-3191 (commit d5c91f269eb4, already closed/dropped -- filed below) via src/frob/check/_python.py::_DEFAULT_TY_TARGET_PLATFORMS
- DRIFT002  src/frob/check/_python.py  -> attributed to T-3191 (commit d5c91f269eb4, already closed/dropped -- filed below) via src/frob/check/_python.py::_DEFAULT_TY_TARGET_PLATFORMS
- REF002  src/frob/tickets/_done_report.py  -> attributed to T-3195 (commit 46b172704c70, already closed/dropped -- filed below) via src/frob/tickets/_done_report.py::_CHANGED_HEADING
- unresolved-attribute  scripts/fleet_status.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- unresolved-attribute  tests/system/test_fleet_status_ground_truth.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- unresolved-attribute  tests/test_app_daemon_proxy.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- unresolved-attribute  tests/test_coverage_wait_shared.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- unresolved-attribute  tests/test_serve_leases.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- unresolved-attribute  tests/test_serve_socket.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- unresolved-attribute  tests/test_ticket_land.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- unresolved-attribute  tests/test_ticket_leases.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- unresolved-attribute  tests/test_ticket_reconcile.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- unresolved-attribute  tests/test_tickets_parent.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- unresolved-attribute  tests/test_tickets_priority.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- unresolved-attribute  tests/unit/test_conftest_stackdump.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- unresolved-attribute  tests/unit/test_coordinator_scripts.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- unresolved-attribute  tests/unit/test_land_finish_guard.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- unresolved-attribute  tests/unit/test_land_lock_liveness.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- unresolved-attribute  tests/unit/test_process_lock.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- unresolved-attribute  tests/unit/test_rapid_sweep.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- unresolved-attribute  tests/unit/test_stackdump.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- unresolved-attribute  tests/unit/test_ticket_store.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.