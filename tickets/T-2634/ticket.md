---
id: T-2634
title: 'Self-conform/mutation-audit/threat cluster: 6 tests red on main, design vs
  live-repo drift'
state: done
kind: bug
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/strata/test_selfconform.py
- tests/unit/strata/test_conform_eval_needle.py
- tests/unit/strata/test_mutation_audit.py
- tests/unit/strata/test_threat.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/strata/test_threat.py::TestCaughtByAuditExhaustive::test_every_shipped_entry_has_a_substantive_caught_by
- tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_every_may_is_load_bearing
- tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_second_detector_gaps_are_exactly_the_disclosed_app_level_kinds
designated_repro_test: tests/unit/strata/test_threat.py::TestCaughtByAuditExhaustive::test_every_shipped_entry_has_a_substantive_caught_by
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Filed from T-2623's tests/unit/ red-test sweep (measured at main sha
5a15dbd92, 18 red of 5237 collected).

Six tests in the strata self-conformance / mutation-audit / threat-model
cluster are red on unmodified main -- all assert the shipped repo design
(design/frob.strata) or its derived catalogs conform to the live codebase,
and all are failing the same general way: the live repo has drifted ahead
of what the self-model / threat catalog / mutation-audit fixtures declare.

  - tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
    (SYS107: node 'testsuite' binds 598 file(s), more than the design
    declares)
  - tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_repo_unrestricted_scan_is_clean
    (same SYS107 shape)
  - tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch::test_real_repo_design_selfconform_has_no_eval_gap
  - tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_every_may_is_load_bearing
  - tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_second_detector_gaps_are_exactly_the_disclosed_app_level_kinds
  - tests/unit/strata/test_threat.py::TestCaughtByAuditExhaustive::test_every_shipped_entry_has_a_substantive_caught_by
    (DEFAULT_BENIGN_CAPABILITIES: assert 17 == 16 -- a new capability was
    added to the live catalog without updating this test's expected count)

Not yet determined per-test whether the fix is updating design/frob.strata
(product) or the test's own expected constants (stale fixture) -- needs a
real investigation, one at a time, not a blanket update. Do NOT weaken any
of these guards; they are working as designed by catching real drift.

Not fixed in T-2623 due to a time-boxed land window (T-2611 draining the
fleet for a repo-wide renormalization land).