---
id: T-1844
title: 'post-land sweep regression from T-1834: 2 new error(s) (PERF003, PERF004)'
state: done
kind: bug
origin: agent
created: '2026-08-08'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/strata/_policy.py
- docs/strata/policy.md
- tests/unit/strata/test_policy.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/strata/policy.md
  reason: AFFECT001 requires updating this doc anchor in the same diff as the find_policy_weakenings
    perf fix
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/strata/test_policy.py
  reason: existing tests cover find_policy_weakenings/_at_call_require_weakenings,
    needed as evidence for the perf fix
  actor: logan
  at: '2026-08-08'
evidence:
- tests/unit/strata/test_policy.py::TestRefinementMonotonicity::test_at_call_require_dropped_arg_detected
- tests/unit/strata/test_policy.py::TestRefinementMonotonicity::test_confine_use_broadened_home_detected
- tests/unit/strata/test_policy.py::TestRefinementMonotonicity::test_mediate_swapped_mediator_detected
- tests/unit/strata/test_policy.py::TestRefinementMonotonicity::test_no_finding_when_child_only_strengthens
- tests/unit/strata/test_policy.py::TestRefinementMonotonicity::test_no_finding_when_child_never_overlaps_parent_scope
- tests/unit/strata/test_policy.py::TestRefinementMonotonicity::test_forbid_call_never_flagged_even_when_child_narrows
designated_repro_test: null
threat: null
component: null
---
The deferred post-land unscoped sweep (T-1684) for T-1834 at commit a0c2d601c29fe5183bdbb01d315a03d1cd1e4247 found 2 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- PERF003  src/frob/strata/_policy.py
- PERF004  src/frob/strata/_policy.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- PERF003  src/frob/strata/_policy.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/strata/_policy.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.