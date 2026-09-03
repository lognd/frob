---
id: T-3624
title: 'windows diag round 10: instrument the 1.6s frob-interrupted'
state: done
kind: bug
origin: human
created: '2026-09-01'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
- tests/test_ci_workflow_matrix.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_ci_workflow_matrix.py::TestWindowsDiagStepDoesNotGateTheJob::test_diag_python_prints_liveness_marker_before_anything_else
- tests/test_ci_workflow_matrix.py::TestWindowsDiagStepDoesNotGateTheJob::test_diag_python_wraps_main_call_in_baseexception_handler
- tests/test_ci_workflow_matrix.py::TestWindowsDiagStepDoesNotGateTheJob::test_diag_step_has_breadcrumbs_around_every_major_block
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Run 33466891764: T-3619's fixes are verified correctly placed
($ErrorActionPreference='Continue' first line; empty commit inside
Push-Location; fixture HAS a HEAD -- no gitio warning this run). Yet the
step STILL printed only:

  frob: interrupted        (at ~1.6s elapsed)

and exited 1 WITHOUT reaching any of the script's own Write-Host lines
(no "frob check diag exit code", no discriminator verdict). Two facts to
explain: (a) frob check on a valid tiny fixture exits "frob: interrupted"
in ~1.5s on win32 -- an INTERRUPT at startup, independent of the earlier
commitless-repo gitio failure (that got fixed and the message persists);
note the contrast: the SUITE's frob-check child on win32 HANGS >120s
(test_cli_check.py pytest-timeout), while this isolated step's child
"interrupts" at 1.5s -- different env/cwd, possibly the same underlying
bug at different phases. (b) the pwsh script terminates without running
its remaining lines even under ErrorActionPreference=Continue.

Round 10 = INSTRUMENTATION, not another guess:
1. Breadcrumbs: Write-Host markers before and after every block
   (fixture setup done / diag file written / about to invoke uv /
   uv returned code X). Whichever marker is the last to print localizes
   the kill point.
2. Run the child via cmd to remove pwsh native-command semantics
   entirely: cmd /c "uv run --project %GITHUB_WORKSPACE% python
   <diag.py> 1>diag.out 2>diag.err & echo child-exit=%ERRORLEVEL%" then
   Get-Content both files -- output survives even if pwsh's own stream
   handling is the killer.
3. In the diag python file, FIRST line: print("diag-python-alive",
   flush=True); wrap the frob main() call in try/except BaseException
   printing repr + traceback to the diag.out file before re-raising --
   so "interrupted" gets a stack. Suspect list for the interrupt:
   T-3565's SIGBREAK signal.signal handler (win32-specific, registered
   at import/startup), or a console-control event delivered to the
   child process group when a parent stream closes.
4. Keep the elapsed-time discriminator; the step must still exit 0 on
   any non-hang outcome.
Scope: .github/workflows/ci.yml + tests/test_ci_workflow_matrix.py.
Related open ticket: T-3620 (opaque "frob: interrupted" on commitless
repos) -- if the stack from step 3 shows the same code path, note it
there; the opaque-message fix belongs in frob itself under T-3620.