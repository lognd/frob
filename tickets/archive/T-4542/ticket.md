---
id: T-4542
title: 'post-land sweep regression from T-4510: 1 new (rule, file) identit(ies), 2
  finding(s) (WIRE002)'
state: dropped
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
acceptance:
- text: 'bound([''tests/unit/gates/test_wire002_live_repo.py::test_wire002_zero_against_live_repo'']):
    both frob:waive WIRE001 directives in src/frob/dup/_legacy_cs.py carry follow_up="T-4542"
    and WIRE002 reports zero findings against the live repo'
  evidence: []
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

## Drop reason
- 2026-09-19: T-1983: auto-dropped by the deferred post-land sweep -- every (rule, file) identity this ticket named (WIRE002 src/frob/dup/_legacy_cs.py) is absent from a direct re-check of exactly the 824 named (rule, file) identit(ies) (not a full sweep) that completed with no failed/silent tool stage at doable's deferred sweep (T-2521: this drop only fires when that measurement itself completed -- no budget deferral, no failed/silent tool stage -- never on an unmeasured or partial run), i.e. no longer reproduces. If this is wrong (a flaky/incomplete measurement), re-file with `frob check --only <gate>` evidence attached.
