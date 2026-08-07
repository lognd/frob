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
scope:
- src/frob/gates/**
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestNativeTestCollectors::test_ts_directive_resolves_via_real_vitest_node_id
- tests/test_gates.py::TestNativeTestCollectors::test_ts_structural_only_edge_no_longer_credited
- tests/test_gates.py::TestNativeTestCollectors::test_ts_no_longer_in_native_extensions
- tests/test_gates.py::TestNativeTestCollectors::test_load_tests_merges_all_four_collectors
designated_repro_test: null
acceptance:
- text: GIVEN a vitest project with a frob:tests directive naming a real vitest test
    WHEN gates run THEN the edge resolves against the collected id and the structural
    fallback no longer credits unverified ts edges
  evidence:
  - tests/test_gates.py::TestNativeTestCollectors::test_ts_directive_resolves_via_real_vitest_node_id
  - tests/test_gates.py::TestNativeTestCollectors::test_ts_structural_only_edge_no_longer_credited
  - tests/test_gates.py::TestNativeTestCollectors::test_ts_no_longer_in_native_extensions
  - tests/test_gates.py::TestNativeTestCollectors::test_load_tests_merges_all_four_collectors
threat: null
component: null
---
T-0587 built real vitest/ctest collectors (collect_ts_tests, collect_cpp_tests in src/frob/testing/_collect.py, exported from frob.testing) but left frob.gates untouched (out of T-0587's declared scope, src/frob/testing/ only). This ticket wires collect_ts_tests/collect_cpp_tests into frob.gates test-evidence loading (_load_tests, alongside collect_python_tests/collect_rust_tests) so frob:tests directives on TS/C/C++ resolve against REAL collected node ids, and retires _edge_is_native_unverified's structural name/path fallback for those languages once real collection exists (per T-0552's original plan).