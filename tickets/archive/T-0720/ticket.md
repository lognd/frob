---
id: T-0720
title: Add pytest.mark.timeout overrides to slow system tests
state: done
kind: bug
origin: human
created: '2026-07-22'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/system/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/system/test_scaffold_dx.py::test_python_toolchain_scaffold_passes_check_immediately[python-tool]
- tests/system/test_scaffold_dx.py::test_all_registered_types_render_without_error
- tests/system/test_natives_build_integration.py::test_build_natives_compiles_and_imports_real_crate
designated_repro_test: null
evidence_changes:
- old_node: tests/system/test_scaffold_dx.py::test_python_tool_scaffold_passes_check_immediately
  new_node: tests/system/test_scaffold_dx.py::test_python_toolchain_scaffold_passes_check_immediately[python-tool]
  reason: T-3277 parametrized this test for multi-scaffold-type coverage; same test
    content for python-tool, new node id
  actor: logan
  at: '2026-08-28'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-0692 added a global 120s/thread pytest-timeout default (pyproject.toml addopts). tests/system/test_scaffold_dx.py (pytest.mark.slow, spawns uv sync + a real venv + full lint/typecheck/test/frob-check pipeline) legitimately runs well over 120s and needs an explicit @pytest.mark.timeout(N) override (and an audit of any other tests/system/** file that might exceed 120s) so it does not start failing under the new default. Out of T-0692's docs/guides+config-only scope; filed per that ticket's Done report.