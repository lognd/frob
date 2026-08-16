---
id: T-2174
title: 'post-land sweep regression from T-2172, T-2156: 2 new (rule, file) identit(ies),
  1 finding(s) (ARCH001, DUP001)'
state: done
kind: bug
origin: agent
created: '2026-08-11'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/graph/callgraph.py
- tests/unit/verify/test_attribution_module_scope.py
evidence_scope:
- tests/unit/test_callgraph_module_scoped.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_callgraph_module_scoped.py::TestBuildReferenceGraphModuleScoped::test_does_not_cross_wire_same_named_helpers_in_unrelated_files
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
The deferred post-land unscoped sweep (T-1684) for T-2172, T-2156 at commit 80ddbb9916018b777820975bdc06700524c461ff found 2 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (2), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 1 actual finding(s) across those 2 identit(ies).

New (rule, file) identit(ies) filed here:

- ARCH001  src/frob/graph/callgraph.py
- DUP001  tests/unit/verify/test_attribution_module_scope.py

T-2009: 2 lands (T-2172, T-2156) landed between the previous sweep's baseline and the commit THIS sweep actually measured (the sweep is deliberately detached, off the land critical path -- T-1684 -- so other agents' lands can land in the window before it runs). Which specific land introduced which finding below could not be determined without re-measuring at each intermediate commit; this ticket is filed against all of them rather than falsely pinned on T-2172, T-2156 alone (the one that happened to spawn this sweep process).

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- ARCH001  src/frob/graph/callgraph.py  -> attributed to T-2156 (commit 7589f5a1f22d, already closed/dropped -- filed below) via src/frob/graph/callgraph.py::_local_imports_by_path
- DUP001  tests/unit/verify/test_attribution_module_scope.py  -> attributed to T-2156 (commit 7589f5a1f22d, already closed/dropped -- filed below) via tests/unit/verify/test_attribution_module_scope.py::TestAttributionDoesNotCrossFileOnSameNamedHelper

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.