---
id: T-0142
title: standalone frob check crashes FileNotFoundError when ruff/ty binaries absent
  -- wheel declares no tool deps
state: done
kind: bug
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- pyproject.toml
- src/frob/check/**
- src/frob/process/**
- tests/**
- docs/guides/install.md
- tickets.md
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_check_tool_unavailable.py::TestToolUnavailableResult::test_shape_is_a_failing_diagnostic
- tests/unit/test_check_tool_unavailable.py::TestRuffUnavailable::test_run_ruff_missing_binary_returns_failing_results
- tests/unit/test_check_tool_unavailable.py::TestRuffUnavailable::test_ruff_format_result_missing_binary_returns_failing_result
- tests/unit/test_check_tool_unavailable.py::TestTyUnavailable::test_run_ty_missing_binary_returns_failing_result
- tests/unit/test_check_tool_unavailable.py::TestCargoUnavailable::test_run_cargo_missing_binary_returns_failing_result
- tests/unit/test_check_tool_unavailable.py::TestCargoUnavailable::test_run_cargo_fmt_check_missing_binary_returns_failing_result
- tests/unit/test_check_tool_unavailable.py::TestCargoUnavailable::test_run_cargo_test_missing_binary_returns_failing_result
- tests/unit/test_check_tool_unavailable.py::TestTscUnavailable::test_run_tsc_missing_npx_returns_failing_result
- tests/unit/test_check_tool_unavailable.py::TestCheckResultRendersUnavailableTool::test_as_text_shows_unavailable_tool_line
designated_repro_test: null
threat: null
component: null
---
The T-0133/T-0135 standalone CI job (bare wheel, clean venv) fails its no-traceback assertion: frob check's _run_ruff shells out to 'ruff' which the wheel neither declares as a dependency nor guards against being absent -- FileNotFoundError propagates through _run_tasks_concurrently as a raw traceback. Same exposure for ty and any other spawned tool. Fix BOTH layers: (1) declare ruff (and ty) as real [project] dependencies so a standalone install is fully functional out of the box (they are pip-installable; pin compatibly with the dev pins); (2) defense in depth per the natives-less precedent -- a missing tool binary becomes a typed ToolResult failure ('tool unavailable: ruff -- install X or use make install-tool') instead of an exception, covered by a monkeypatched-absence test. The CI job must then pass un-gated.