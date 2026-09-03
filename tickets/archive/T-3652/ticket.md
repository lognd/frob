---
id: T-3652
title: stale matrix-test window misses Start-Process --project arg (T-3648 growth)
state: done
kind: bug
origin: human
created: '2026-09-01'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_ci_workflow_matrix.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_ci_workflow_matrix.py::TestWindowsDiagStepResolvesFrobCheckoutEnv::test_windows_diag_step_uv_run_pins_project_to_checkout
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Run 33513484322, ubuntu AND macOS, deterministic:
  tests/test_ci_workflow_matrix.py::TestWindowsDiagStepResolvesFrobCheckoutEnv::
  test_windows_diag_step_uv_run_pins_project_to_checkout FAILED

The T-3597-era assertion checks for the old inline `uv run --project ...
python ...` string; T-3637/T-3648 rewrote the invocation to Start-Process
with an -ArgumentList. Update the assertion to verify the SAME contract
(dependency resolution pinned to the checkout, not the fixture) against
the Start-Process argument list. Do not delete the contract check.
Scope: tests/test_ci_workflow_matrix.py.

Root cause measured locally: the assertion's 8000-char window from the
step heading no longer reaches the actual `-ArgumentList "run",
"--project", "$env:GITHUB_WORKSPACE", ...` line -- T-3648's added
instrumentation (SIGINT/SIGBREAK handler, FROB_WIN32_SPAWN_DEBUG) grew
the step text so the real invocation now sits ~9527 chars past the
heading, past the window; only an unrelated prose comment mentioning
"--project" falls inside the old window, so the assertion's exact
literal never matches. Fix: widen the window and/or match the true
Start-Process -ArgumentList shape (each argument its own array element:
`"--project", "$env:GITHUB_WORKSPACE",`), preserving the same contract
the docstring documents (dependency resolution pinned to the checkout).