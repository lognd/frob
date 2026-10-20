+++
id = "01M336K75EAMNYHPARXTJA7QNM"
title = "TEST002/3/4/7/9 test-gate detectors miscount/misfire on real fixtures"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 2
reporter = "human"
created = "2026-09-22T00:00:00Z"
updated = "2026-09-22T00:00:02Z"
aliases = ["T-5294"]
labels = ["milestone:0.534.0"]
scope = ["tests/gates_suite/test_test_gate.py", "src/frob/gates/__init__.py"]
+++

gh run 35717833933; re-verified on dev tip 3acf8c6b30: 7 failures in tests/gates_suite/test_test_gate.py -- test_test003_satisfied_by_parametrized_case_with_dot_in_case_id, test_test003_satisfied_by_parametrized_test_node_id, test_test004_passes_with_enough_e2e, test_test002_parametrized_test_counts_each_case, test_test003_satisfied_by_proptest_macro_block, test_test009_satisfied_by_e2e_edge, test_test007_passes_when_boundary_tested. All are 'expected pass, gate still flags' shape -- detector regressions, not fixture drift.
