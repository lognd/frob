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
scope:
- tests/system/test_scaffold_dx.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/system/test_scaffold_dx.py::test_python_tool_scaffold_passes_check_immediately
designated_repro_test: null
acceptance:
- text: GIVEN the slow scaffold test WHEN the suite runs under the global 120s ceiling
    THEN the test carries its own measured override and passes cold-cache
  evidence:
  - tests/system/test_scaffold_dx.py::test_python_tool_scaffold_passes_check_immediately
threat: null
component: null
---
Lost draft from T-0692 (pytest-timeout guard): tests/system/test_scaffold_dx.py spawns a real uv sync + venv + full pipeline; measured 4.52s locally (25x margin under the 120s ceiling) but cold-cache CI could erode it. Add an explicit pytest.mark.timeout override with a measured-based value and a comment. T-0692 reviewer judged deferral safe-to-land; this is the standing home.