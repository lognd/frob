---
id: T-3436
title: tests/test_coverage.py::TestPyprojectDeclaresCoverageConcurrency asserts sigterm=True,
  contradicts T-3420's sigterm=false fix
state: dropped
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-3275 (unrelated ticket): tests/test_coverage.py::TestPyprojectDeclaresCoverageConcurrency::test_pyproject_declares_concurrency_and_sigterm asserts pyproject.toml's [tool.coverage.run].sigterm is True. T-3420 (landed 344eba4dbafbca5c580b055c2fd2614dd32e825a) deliberately changed that to sigterm=false (fixes a SIGTERM-handler re-entrancy deadlock, see that ticket's Done report) but did not know this test existed / did not update it -- T-3420's own frob check/frob test runs did not catch it (test not in its touched set). This test now fails on main. Update the assertion to sigterm=False and its docstring to reference T-3420's fix instead of T-1235's Loss B fix (or fold both rationales together).

## Drop reason
- 2026-08-29: fixed directly in T-3275 since tests/test_coverage.py was already in that ticket's scope and this was blocking its own test run; see T-3275's Done report
