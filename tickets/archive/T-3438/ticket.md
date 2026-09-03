---
id: T-3438
title: frob vet hook mode leaks the frob claude sync config nag to stderr; hook mode
  must be silent
state: done
kind: bug
origin: agent
created: '2026-08-29'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/claude_runner.py
- src/frob/app/telemetry/__init__.py
- src/frob/__main__.py
- tests/system/test_cli_vet.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_main_entry.py::TestVetHookSuppressesStartupWarnings::test_vet_hook_suppresses_startup_warnings
- tests/unit/test_main_entry.py::TestVetHookSuppressesStartupWarnings::test_vet_without_hook_still_warns
- tests/system/test_cli_vet.py::TestHookMode::test_non_install_command_fast_exits_zero
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: f58091d391b98e4ce680a38aab6f5cdf335a2ef1
---
MEASURED on GitHub Actions run 33282540898 (ubuntu-latest, HEAD b94cea5d0, 2026-08-30) -- the first run that completed to 100% (20 failures of 12689). This failure is in the cross-platform set (fails on macOS too unless noted). Reproduce locally by node id with -p no:xdist first; if it passes locally, the defect is an environment dependency (git identity, tmp path shape, missing tool, timing) and the fix must make the test hermetic, not skip it.

FAILING: tests/system/test_cli_vet.py::TestHookMode::test_non_install_command_fast_exits_zero
    AssertionError: assert "Claude confi...laude sync`\n" == ""
The `frob vet` hook mode must produce NO stderr for a non-install command, but the "Claude config ... run frob claude sync" nag is printed. Hook mode is machine-consumed; find the single home of the nag (git grep "frob claude sync" -- src) and suppress it whenever the invocation is a hook/agent context (or gate it on a TTY), with a must-fire test that a normal interactive `frob check` still prints it.