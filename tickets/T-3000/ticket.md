---
id: T-3000
title: 'Verbose flag after a subcommand is silently accepted and ignored: only the
  pre-subcommand position works'
state: queued
kind: bug
origin: human
created: '2026-08-26'
priority: medium
blocked_by:
- T-2954
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_ticket_runner_quiet.py::TestDiagnosticLogCtx::test_default_clamps_frob_tree_but_pins_runner_output
- tests/test_ticket_runner_quiet.py::TestDiagnosticLogCtx::test_verbose_skips_the_clamp
- tests/test_ticket_runner_quiet.py::TestDiagnosticLogCtx::test_global_frob_verbose_env_var_also_skips_the_clamp
- tests/test_ticket_runner_quiet.py::TestDiagnosticLogCtx::test_global_frob_log_level_env_var_also_skips_the_clamp
- tests/test_ticket_runner_quiet.py::TestDiagnosticLogCtx::test_no_verbose_signal_at_all_still_clamps
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
