---
id: T-5219
title: 'flag-coverage gate: 2 CLI flags (clean_sweep_worktrees, ticket_wait_s) parse
  but never reach AppConfig'
state: queued
kind: bug
origin: human
created: '2026-09-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/config.py
- tests/unit/test_app_config_flag_coverage.py
- tests/unit/test_flag_coverage_gate.py
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
Found while burning down fresh CI run 35654510898, re-verified on current dev tip. tests/unit/test_app_config_flag_coverage.py::TestFindDroppedCliFlags::test_current_tree_has_zero_dropped_flags and tests/unit/test_flag_coverage_gate.py::TestFlagCoverageGate::test_this_repos_own_frob_toml_reports_zero both fail: 2/386 CLI flags parse but never reach AppConfig -- 'clean_sweep_worktrees' and 'ticket_wait_s'. A recently landed feature added a --clean-sweep-worktrees and/or --ticket-wait-s CLI flag whose parsed value is never threaded into AppConfig (or the corresponding AppConfig field/wiring was renamed/dropped without updating the flag). Fix: trace both flag names through src/frob/app/_cli_parsers/ to src/frob/app/config.py and either wire the missing AppConfig field or remove the now-dead flag.