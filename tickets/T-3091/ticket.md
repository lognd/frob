---
id: T-3091
title: TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root
  fails on main
state: queued
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_render_lint.py
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
Found while working T-3031 (root-cause investigation for
TestCheckTypescript::test_clean_ts_passes_tsc). tests/system/
test_cli_check.py::TestGitlessTargetGateSeverity::
test_render_lint_gate_warns_not_errors_on_gitless_root fails on
unmodified main -- confirmed independently of T-3031's own fix by
reverting T-3031's diff and re-running this one test in isolation (still
fails identically at the parent commit).

Out of T-3031's own declared scope (src/frob/gates/_refs.py, the
TestCheckTypescript fixture) -- render_lint_gate's gitless-target
severity degrade is a different gate and a different module.
