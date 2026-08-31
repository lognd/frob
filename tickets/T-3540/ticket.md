---
id: T-3540
title: 'Windows CI: Start-Process/Wait-Process console-sharing causes an early KeyboardInterrupt,
  aborting the suite at ~1%'
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
body_changes:
- mode: append
  reason: BUG002 cannot be satisfied by a local test
  actor: logan
  at: '2026-08-31'
  old_length: 2940
  new_length: 3544
evidence:
- tests/unit/test_release_workflow_gate.py::TestCiWindowsLegAdvisoryOnly::test_build_job_continue_on_error_is_windows_only
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-3511 (re-measurement after the five T-3505 primitive fixes): the newest completed windows-latest run (33353658750, HEAD 2654ca1ff, job id 99371614987) again DID-NOT-COMPLETE -- exitstatus=2 INTERRUPTED, collected=12924 tests, only reached ~1% (129/12924) before a bare KeyboardInterrupt killed the whole pytest session at threading.py:359, only ~49s after xdist finished "bringing up nodes" (03:26:42 -> 03:27:31) and nowhere near the step's own 1500s (25m) Wait-Process budget or pytest-timeout's --timeout=120 per-test threshold. Only 3 failures were visible before the interrupt, all tests/gates/test_comment_placement.py (the known os.sep symref bug, filed separately -- see docs/design/windows-portability.md).

RULED OUT: pytest-timeout's --timeout-method=thread does NOT raise KeyboardInterrupt on expiry -- read .venv/lib/python3.11/site-packages/pytest_timeout.py::timeout_timer directly: it dumps thread stacks and calls os._exit(1), a hard process exit, never an interrupt signal. No test in this run reached anywhere near 120s (the whole session ran only 49s). No os.kill(CTRL_C_EVENT)/GenerateConsoleCtrlEvent call exists anywhere under tests/ or src/ (grepped, zero hits).

LEADING HYPOTHESIS: .github/workflows/ci.yml's windows Test step ("Test (windows, timed with hang guard)", T-3250) launches pytest via Start-Process -FilePath uv -ArgumentList run,pytest,-q -NoNewWindow -PassThru then Wait-Process -Timeout $budget. -NoNewWindow means the child process does NOT get its own console/process group -- it shares the parent pwsh step's console. This is a known Windows/PowerShell footgun: any console control event delivered to that shared console (a GitHub Actions hosted-runner heartbeat/cancellation-listener CTRL_BREAK_EVENT broadcast is the well-documented culprit on GH-hosted Windows runners) propagates to EVERY process attached to that console, including the -NoNewWindow child -- and CPython's default Windows console-control handler maps CTRL_BREAK_EVENT/CTRL_C_EVENT to a KeyboardInterrupt raised on the main thread, exactly matching the observed threading.py:359 stack.

FIX: stop sharing the console. Concretely, either (a) drop -NoNewWindow so Start-Process gets its own console/process group (loses inline output capture, needs re-piping via -RedirectStandardOutput/-RedirectStandardError instead), or (b) pass CREATE_NEW_PROCESS_GROUP-equivalent behavior some other way pwsh exposes, or (c) replace the Start-Process/Wait-Process budget wrapper entirely with a mechanism that does not share a console (e.g. a background Start-Job, or a plain "uv run pytest -q" foregrounded under a wrapping timeout.exe/pwsh job with its own console). Verify the fix by re-running windows-latest and confirming the suite reaches a stable completed (not INTERRUPTED) result, or at minimum runs well past the ~1 minute mark this incident shows failing at.

Filed under T-3505 (Windows portability epic).



frob:waive BUG002 reason="this defect (a stray console-shared CTRL_BREAK_EVENT reaching the pytest child on GitHub-hosted Windows runners) only reproduces on real windows-latest CI infrastructure -- there is no local, deterministic way to simulate a hosted-runner console-control broadcast in a pytest node id; the fix (dropping Start-Process -NoNewWindow so the child gets its own console/process group) is verified by re-running windows-latest and observing the suite run past the ~1%/49s point it previously failed at, tracked as a windows-portability re-measurement follow-up, not by a unit test"