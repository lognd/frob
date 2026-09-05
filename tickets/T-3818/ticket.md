---
id: T-3818
title: 'T-3797 regression: check tool-runners render Err(SpawnFailed) as tool_disabled
  instead of tool_unavailable (mac+ubuntu red on test_check_tool_unavailable)'
state: done
kind: bug
origin: human
created: '2026-09-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/check/_python.py
- src/frob/check/_native.py
- src/frob/check/_ts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/check/_python.py
  reason: fix Err(SpawnFailed) rendering at all tool-runner sites
  actor: logan
  at: '2026-09-05'
- op: add
  glob: src/frob/check/_native.py
  reason: fix Err(SpawnFailed) rendering at all tool-runner sites
  actor: logan
  at: '2026-09-05'
- op: add
  glob: src/frob/check/_ts.py
  reason: fix Err(SpawnFailed) rendering at all tool-runner sites
  actor: logan
  at: '2026-09-05'
evidence:
- tests/unit/test_check_tool_unavailable.py::TestRuffUnavailable::test_run_ruff_missing_binary_returns_failing_results
- tests/unit/test_check_tool_unavailable.py::TestRuffUnavailable::test_ruff_format_result_missing_binary_returns_failing_result
- tests/unit/test_check_tool_unavailable.py::TestTyUnavailable::test_run_ty_missing_binary_returns_failing_result
- tests/unit/test_check_tool_unavailable.py::TestCargoUnavailable::test_run_cargo_missing_binary_returns_failing_result
- tests/unit/test_check_tool_unavailable.py::TestCargoUnavailable::test_run_cargo_fmt_check_missing_binary_returns_failing_result
- tests/unit/test_check_tool_unavailable.py::TestCargoUnavailable::test_run_cargo_test_missing_binary_returns_failing_result
- tests/unit/test_check_tool_unavailable.py::TestTscUnavailable::test_run_tsc_missing_npx_returns_failing_result
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
