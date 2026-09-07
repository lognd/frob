---
id: T-4173
title: 'post-land sweep regression from T-4105: 4 new (rule, file) identit(ies) (ARCH103,
  COV001, DRIFT001, DRIFT002)'
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/check/_python.py
- src/frob/gates/_rule_id_scan.py
- src/frob/vet/_bare_toolchain.py
findings:
- - ARCH103
  - src/frob/app/ticket_runner/_land_cmd.py
- - COV001
  - src/frob/vet/_bare_toolchain.py
- - DRIFT001
  - src/frob/gates/_rule_id_scan.py
- - DRIFT002
  - src/frob/check/_python.py
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
---
The deferred post-land unscoped sweep (T-1684) for T-4105 at commit d29fbf1b448a65087e64024113d4abb546c30b3d found 4 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES, not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). The true per-finding count could not be independently re-measured this run (spawn refused/timeout/unparsable) -- re-run `frob check` unscoped against the file(s) below for the exact count before treating this identity count as a completeness claim.

New (rule, file) identit(ies) filed here:

- ARCH103  src/frob/app/ticket_runner/_land_cmd.py
- COV001  src/frob/vet/_bare_toolchain.py
- DRIFT001  src/frob/gates/_rule_id_scan.py
- DRIFT002  src/frob/check/_python.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- ARCH103  src/frob/app/ticket_runner/_land_cmd.py  -> attributed to T-4105 (commit d29fbf1b448a, already closed/dropped -- filed below) via src/frob/app/ticket_runner/_land_cmd.py::_capture_pre_land_baseline -> src/frob/app/ticket_runner/_land_cmd.py::_unscoped_error_findings
- COV001  src/frob/vet/_bare_toolchain.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DRIFT001  src/frob/gates/_rule_id_scan.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DRIFT002  src/frob/check/_python.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.