+++
id = "01M336K76XR0MSFF0ZQDNFEG7N"
title = "COV006 + rule-fixability/known-rule-id regressions found while working T-5294"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "human"
created = "2026-09-22T00:00:00Z"
updated = "2026-09-22T00:00:02Z"
aliases = ["T-5341"]
scope = ["tests/gates_suite/test_coverage.py", "tests/gates_suite/test_sys.py", "src/frob/gates/__init__.py"]
+++

Found while working T-5294 on dev tip 799a877740 (dev had advanced past T-5294's worktree base via concurrent lands): tests/gates_suite/test_coverage.py::TestCoverageGate::test_cov006_flags_test_with_no_call_graph_reachability, test_cov006_violation_carries_edge_src_as_symref, test_cov006_still_fires_when_no_public_wrapper_reaches_the_target, test_cov006_waiver_does_not_blanket_suppress_the_whole_file all fail; tests/gates_suite/test_sys.py::TestRuleFixability::test_checked_in_literal_matches_a_fresh_scan and TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known also fail. Confirmed NOT caused by T-5294's diff (T-5294 only touches _unit_test_edges/_case_count/_edge_has_execution_evidence/_pair_covered around lines 670-1000 and 4680-4950; these failures are in unrelated COV006/_cov006 code around lines 2587-3334 and the sys-gate rule registry). Not re-verified against a fully fresh dev tip beyond that; re-check before acting.
