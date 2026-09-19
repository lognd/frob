---
id: T-0730
title: 'gates: consume vitest/ctest collector node ids in _load_tests/_valid_edges,
  retire the ts/c/cpp structural fallback'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0587
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/**
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: moving DOCARCH001 change-narrative out of the test docstring per T-4420
  actor: logan
  at: '2026-09-19'
  old_length: 610
  new_length: 1351
evidence:
- tests/gates_suite/test_test_gate.py::TestNativeTestCollectors::test_ts_directive_resolves_via_real_vitest_node_id
- tests/gates_suite/test_test_gate.py::TestNativeTestCollectors::test_ts_structural_only_edge_no_longer_credited
- tests/gates_suite/test_test_gate.py::TestNativeTestCollectors::test_ts_no_longer_in_native_extensions
- tests/gates_suite/test_test_gate.py::TestNativeTestCollectors::test_load_tests_merges_all_four_collectors
designated_repro_test: null
acceptance:
- text: GIVEN a vitest project with a frob:tests directive naming a real vitest test
    WHEN gates run THEN the edge resolves against the collected id and the structural
    fallback no longer credits unverified ts edges
  evidence:
  - tests/gates_suite/test_test_gate.py::TestNativeTestCollectors::test_ts_directive_resolves_via_real_vitest_node_id
  - tests/gates_suite/test_test_gate.py::TestNativeTestCollectors::test_ts_structural_only_edge_no_longer_credited
  - tests/gates_suite/test_test_gate.py::TestNativeTestCollectors::test_ts_no_longer_in_native_extensions
  - tests/gates_suite/test_test_gate.py::TestNativeTestCollectors::test_load_tests_merges_all_four_collectors
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-0587 built real vitest/ctest collectors (collect_ts_tests, collect_cpp_tests in src/frob/testing/_collect.py, exported from frob.testing) but left frob.gates untouched (out of T-0587's declared scope, src/frob/testing/ only). This ticket wires collect_ts_tests/collect_cpp_tests into frob.gates test-evidence loading (_load_tests, alongside collect_python_tests/collect_rust_tests) so frob:tests directives on TS/C/C++ resolve against REAL collected node ids, and retires _edge_is_native_unverified's structural name/path fallback for those languages once real collection exists (per T-0552's original plan).

DOCARCH001 cleanup note (T-4420): tests/gates_suite/test_test_gate.py::TestNativeTestCollectors.test_ts_structural_only_edge_no_longer_credited's docstring used to say: 'Acceptance (T-0730): a TS frob:tests edge that only LOOKS like test code by name/path, with NO real collected vitest evidence, no longer gets any TEST001-004 credit at all -- the structural fallback _edge_is_native_unverified used to grant TS (T-0552) is retired for .ts. The edge still exists (so TEST001, no edge at all, stays clean), but it now counts zero cases instead of the one the retired fallback used to grant, so it is a genuine TEST002 finding rather than a silent pass or a TEST013 warning.' Moved here; the test docstring now states only what it verifies.