---
id: T-4429
title: gates._load_tests drops platform_skipped, so COV003 never attributes on Windows
state: done
kind: bug
origin: human
created: '2026-09-11'
priority: critical
parent: T-3505
tier: ticket
sprint: v0.531.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
- docs/modules/gates.md
- tests/gates_suite/test_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/test_testing_collect.py
  reason: T-4409 already leases this file; put the regression test in tests/gates/test_gate_cov.py
    instead
  actor: logan
  at: '2026-09-11'
- op: add
  glob: docs/modules/gates.md
  reason: editing _load_tests, whose frob:doc target is docs/modules/gates.md
  actor: logan
  at: '2026-09-11'
- op: remove
  glob: tests/gates/test_gate_cov.py
  reason: actual test module covering _load_tests/COV003 platform_skipped is tests/gates_suite/test_coverage.py,
    not the guessed path
  actor: logan
  at: '2026-09-11'
- op: add
  glob: tests/gates_suite/test_coverage.py
  reason: actual test module covering _load_tests/COV003 platform_skipped is tests/gates_suite/test_coverage.py,
    not the guessed path
  actor: logan
  at: '2026-09-11'
evidence:
- tests/gates_suite/test_coverage.py::TestCoverageGate::test_load_tests_threads_platform_skipped_through
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED on Windows mirror (winrun), main HEAD acff40c67 (includes T-4382/T-4386/T-4390/T-4408): collect_python_tests correctly returns platform_skipped for POSIX-only modules (tests/unit/test_conftest_stackdump.py, tests/unit/test_stackdump.py, reason SIGUSR1 is POSIX-only) but frob.gates._load_tests (src/frob/gates/__init__.py ~6784) discards it via CollectedTests(node_ids=frozenset(node_ids)), defaulting platform_skipped=(). Confirmed by calling _load_tests(root) directly on the mirror: platform_skipped == (). This is the root cause of all 56 COV003 with zero platform attribution on the Windows CI leg; T-4382/T-4386/T-4390/T-4408 each fixed a stage upstream of collect_python_tests's return value, but that value never reaches the CollectedTests object gates/_cov003 and gates/_test002_platform_skipped read. On Linux invisible since no module is platform_skipped running on posix. Fix: thread platform_skipped through _load_tests's CollectedTests construction. Add a Linux-runnable regression test that feeds the measured Windows shape through _load_tests and asserts platform_skipped survives.