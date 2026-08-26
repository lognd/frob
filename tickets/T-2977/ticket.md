---
id: T-2977
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-2966):
  2 new (rule, file) identit(ies), 2 finding(s) (F401)'
state: in-progress
kind: bug
origin: agent
created: '2026-08-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_lexical_selfcheck.py
- src/frob/gates/_port_selfcheck.py
findings:
- - F401
  - /home/logan/projects/frob/src/frob/gates/_lexical_selfcheck.py
- - F401
  - /home/logan/projects/frob/src/frob/gates/_port_selfcheck.py
evidence_scope:
- tests/unit/gates/test_port_selfcheck.py
- tests/unit/gates/test_detector_scope.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: pure dead-import deletion left by T-2966 extraction; BUG002 cannot be satisfied
    by a failing repro because there is no runtime behavior at the parent commit,
    so the T-1616 no-behavior-change directive is the gates own documented remedy
  actor: logan
  at: '2026-08-26'
  old_length: 1495
  new_length: 2077
evidence:
- tests/unit/gates/test_port_selfcheck.py::TestPort001::test_hardcoded_path_prefix_is_flagged
- tests/unit/gates/test_detector_scope.py::TestDetectorScope::test_tracked_gate_files_filters_to_detector_roots
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-2966) at commit cc1c0b85d965b7b15d81608457f2927a69b67085 found 2 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (2), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 2 actual finding(s) across those 2 identit(ies).

New (rule, file) identit(ies) filed here:

- F401  /home/logan/projects/frob/src/frob/gates/_lexical_selfcheck.py
- F401  /home/logan/projects/frob/src/frob/gates/_port_selfcheck.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- F401  /home/logan/projects/frob/src/frob/gates/_lexical_selfcheck.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- F401  /home/logan/projects/frob/src/frob/gates/_port_selfcheck.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.
frob:no-behavior-change reason="T-2966 extracted the shared _tracked_gate_files
helper into frob.gates._detector_scope and updated both call sites, which left
is_detector_package_file imported but unused in _lexical_selfcheck.py and
_port_selfcheck.py. The fix deletes two dead import bindings and nothing else --
there is no runtime behavior to reproduce at the parent commit, so BUG002 cannot
be satisfied by a failing test (T-1616). The correct evidence is that the
existing gate tests still PASS unchanged after the deletion, which is exactly
what no-behavior-change asserts."