---
id: T-2968
title: 'test_cli_cycle.py: 3 exit-code assertions predate cycle-found=1 CLI contract'
state: queued
kind: bug
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/system/test_cli_cycle.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: 1. test_cycle_exit_zero, test_deep_cycle_exit_zero,
  evidence: []
- text: test_suggest_cycle_exit_zero updated to assert the CLI's documented
  evidence: []
- text: exit code for a real cycle (1), or renamed/reworked if their intent
  evidence: []
- text: was actually to assert something else.
  evidence: []
- text: 2. All three pass locally.
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-2943 (macOS git returncode=128 cluster triage).

tests/system/test_cli_cycle.py::test_cycle_exit_zero,
test_deep_cycle_exit_zero, test_suggest_cycle_exit_zero all assert
r.returncode == 0 against a fixture (cycle_dir / deep_cycle_dir) that
DELIBERATELY contains a real import cycle. frob.app.cycle_runner.run's
own docstring states the CLI "exits 1 (not 0) when real cycles are
found" -- so these three tests' own expectations contradict the CLI's
documented, intended contract; they never reached this assertion before
because the git-returncode=128 fixture bug (fixed by T-2943) masked it.
Reproduced live on Linux, current main, in a natives-built worktree.

Not fixed as part of T-2943 (out of that ticket's git-128 scope): fix
the three assertions to expect returncode==1 for a cycle_dir/
deep_cycle_dir case (matching the documented CLI contract), not the
CLI.
