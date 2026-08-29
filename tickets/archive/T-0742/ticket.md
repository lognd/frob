---
id: T-0742
title: 'test_scaffold_dx: explicit pytest timeout override with measured headroom'
state: done
kind: bug
origin: agent
created: '2026-07-22'
priority: low
parent: T-0692
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/system/test_scaffold_dx.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/system/test_scaffold_dx.py::test_python_toolchain_scaffold_passes_check_immediately[python-tool]
designated_repro_test: null
acceptance:
- text: GIVEN the slow scaffold test WHEN the suite runs under the global 120s ceiling
    THEN the test carries its own measured override and passes cold-cache
  evidence:
  - tests/system/test_scaffold_dx.py::test_python_toolchain_scaffold_passes_check_immediately[python-tool]
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
Lost draft from T-0692 (pytest-timeout guard): tests/system/test_scaffold_dx.py spawns a real uv sync + venv + full pipeline; measured 4.52s locally (25x margin under the 120s ceiling) but cold-cache CI could erode it. Add an explicit pytest.mark.timeout override with a measured-based value and a comment. T-0692 reviewer judged deferral safe-to-land; this is the standing home.