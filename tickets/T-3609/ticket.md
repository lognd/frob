---
id: T-3609
title: 'Windows diag step: stderr redirect kills script under pwsh Stop; continue-on-error
  smuggled onto non-windows guard (T-3604 round 8)'
state: done
kind: bug
origin: human
created: '2026-08-31'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_ci_workflow_matrix.py::TestWindowsDiagStepDoesNotGateTheJob::test_step_has_no_continue_on_error
- tests/test_ci_workflow_matrix.py::TestWindowsDiagStepDoesNotGateTheJob::test_diag_invocation_does_not_redirect_stderr
- tests/test_ci_workflow_matrix.py::TestWindowsDiagStepDoesNotGateTheJob::test_test_step_is_untouched_and_still_windows_only
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Run 33451274911 measured two defects in T-3604's diag step:

1. The diag step DIED in 2s with zero output, exit 1, before its first
   Write-Host. Cause: T-3604 added `2>$stderrFile` on the `uv run
   --project ... python ...` line. GitHub Actions' pwsh shell runs with
   $ErrorActionPreference='Stop', and redirecting a NATIVE command's
   stderr to a file under Stop converts uv's first stderr line (its
   resolver chatter) into a terminating NativeCommandError -- the
   script dies at that line, stderr swallowed. Round 6's version worked
   precisely because stderr was NOT redirected. Fix: set
   $ErrorActionPreference = 'Continue' immediately before the uv run
   line (restore Stop after), or drop the 2> redirect entirely and let
   stderr interleave on the console -- it is a diagnostic, interleaved
   is fine. Keep the elapsed-time discriminator.

2. T-3604's `continue-on-error: true` on the step tripped the repo's
   own guard test on BOTH POSIX legs:
   tests/unit/test_release_workflow_gate.py::
   TestCiWindowsLegAdvisoryOnly::
   test_no_step_level_continue_on_error_smuggled_onto_other_legs --
   "the advisory boundary must stay job-level and windows-only". That
   one failing test was the ONLY macOS suite failure this run. Fix:
   REMOVE the step-level continue-on-error. It is redundant now --
   T-3604's own script-side fix makes the script exit 0 for every
   no-hang outcome, and the only nonzero left is a genuine
   watchdog-fired hang, which SHOULD fail the (job-level-advisory)
   windows job loudly. Do not modify the guard test; it is correct.

Context: the Windows Test step this run reached test_cli_check.py and
got INTERRUPTED at ~2m17s (pytest-timeout 120s on its first
`python -m frob check` child) -- the very hang the diag exists to
reproduce, so once this fix makes the diag actually run (unbudgeted,
per T-3604), the next run is the real reproduction attempt.