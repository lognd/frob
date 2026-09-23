---
id: T-5341
title: COV006 + rule-fixability/known-rule-id regressions found while working T-5294
state: done
kind: bug
origin: human
created: '2026-09-22'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
points: 3
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/gates_suite/test_coverage.py
- tests/gates_suite/test_sys.py
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '2'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
evidence:
- tests/gates_suite/test_coverage.py::TestCoverageGate::test_cov006_flags_test_with_no_call_graph_reachability
- tests/gates_suite/test_coverage.py::TestCoverageGate::test_cov006_still_fires_when_no_public_wrapper_reaches_the_target
- tests/gates_suite/test_coverage.py::TestCoverageGate::test_cov006_violation_carries_edge_src_as_symref
- tests/gates_suite/test_coverage.py::TestCoverageGate::test_cov006_waiver_does_not_blanket_suppress_the_whole_file
- tests/gates_suite/test_sys.py::TestRuleFixability::test_checked_in_literal_matches_a_fresh_scan
- tests/gates_suite/test_sys.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5341
branch: t-5341
---
Found while working T-5294 on dev tip 799a877740 (dev had advanced past T-5294's worktree base via concurrent lands): tests/gates_suite/test_coverage.py::TestCoverageGate::test_cov006_flags_test_with_no_call_graph_reachability, test_cov006_violation_carries_edge_src_as_symref, test_cov006_still_fires_when_no_public_wrapper_reaches_the_target, test_cov006_waiver_does_not_blanket_suppress_the_whole_file all fail; tests/gates_suite/test_sys.py::TestRuleFixability::test_checked_in_literal_matches_a_fresh_scan and TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known also fail. Confirmed NOT caused by T-5294's diff (T-5294 only touches _unit_test_edges/_case_count/_edge_has_execution_evidence/_pair_covered around lines 670-1000 and 4680-4950; these failures are in unrelated COV006/_cov006 code around lines 2587-3334 and the sys-gate rule registry). Not re-verified against a fully fresh dev tip beyond that; re-check before acting.