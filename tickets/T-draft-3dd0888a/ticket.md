---
id: T-draft-3dd0888a
title: 'post-land sweep regression from T-4510: 1 new (rule, file) identit(ies), 2
  finding(s) (WIRE002)'
state: queued
kind: bug
origin: agent
created: '2026-09-16'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/dup/_legacy_cs.py
findings:
- - WIRE002
  - src/frob/dup/_legacy_cs.py
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
The deferred post-land unscoped sweep (T-1684) for T-4510 at commit 79bce23d3b8da7062add264866d614b5502c3c25 found 6 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (1), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 2 actual finding(s) across those 1 identit(ies).

New (rule, file) identit(ies) filed here:

- WIRE002  src/frob/dup/_legacy_cs.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- ARCH103  src/frob/doctor.py  -> attributed to T-4501 (commit 546338d6b8a7, already closed/dropped -- filed below) via src/frob/doctor.py::DoctorReport -> src/frob/doctor.py::_DerivedArtifactDrift
- COV002  src/frob/doctor.py  -> attributed to T-4501 (commit 546338d6b8a7, already closed/dropped -- filed below) via src/frob/doctor.py::DoctorReport -> src/frob/doctor.py::_DerivedArtifactDrift
- COV002  tests/unit/test_doctor.py  -> attributed to T-4501 (commit 546338d6b8a7, already closed/dropped -- filed below) via tests/unit/test_doctor.py::TestUnityEditorStatus
- PERF004  src/frob/doctor.py  -> attributed to T-4501 (commit 546338d6b8a7, already closed/dropped -- filed below) via src/frob/doctor.py::DoctorReport -> src/frob/doctor.py::_DerivedArtifactDrift
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4511.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- WIRE002  src/frob/dup/_legacy_cs.py  -> attributed to T-4510 (commit 79bce23d3b8d, already closed/dropped -- filed below) via src/frob/dup/_legacy.py::_scan_cs_file -> src/frob/dup/_legacy_cs.py::_collect_locals_cs -> src/frob/dup/_legacy_cs.py::_collect_assigned_names_cs -> src/frob/dup/_legacy_cs.py::_harvest_cs_variable_declaration

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.