---
id: T-0123
title: register pytest 'slow' marker in pyproject.toml
state: done
kind: docs
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- pyproject.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/system/test_cli_perf.py::TestPerfProfileAndHeat::test_profile_then_heat_shows_hot_function
designated_repro_test: null
threat: null
component: null
---
Found while working T-0089. tests/system/test_scaffold_dx.py uses pytestmark = pytest.mark.slow but the marker is never registered via [tool.pytest.ini_options] markers, so every run emits a PytestUnknownMarkWarning. Add markers = ["slow: ..."] to pyproject.toml's pytest config.
## Done report

Registered markers = ["slow: long-running system tests excluded from
quick loops"] under [tool.pytest.ini_options]. Verified: no
PytestUnknownMarkWarning on system-test runs; -m slow selects the
scaffold-dx tests; collection still parses cleanly.