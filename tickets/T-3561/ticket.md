---
id: T-3561
title: T-3531 log_level=WARNING broke 7 log-assertion tests; set per-test capture
  levels
state: queued
kind: bug
origin: agent
created: '2026-08-31'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_debt_runner.py
- tests/test_deprecated_runner.py
- tests/unit/test_app_runners_t0875_leaf_collision.py
- tests/test_ticket_work_and_land_finish.py
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
Run 33367854833: the global log_level=WARNING (T-3531, correct for CI noise) means caplog/capsys no longer carries the INFO lines these tests assert. Fix each test to request its own level (caplog.set_level(logging.INFO, logger=...) or the runner-output equivalent) -- never revert the global. Affected: tests/test_debt_runner.py (2), tests/test_deprecated_runner.py (3), tests/unit/test_app_runners_t0875_leaf_collision.py (1), tests/test_ticket_work_and_land_finish.py::TestWork::test_fleet_context_reports_the_bound_agent_env_exports_computed (1).