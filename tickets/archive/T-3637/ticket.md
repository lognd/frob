---
id: T-3637
title: 'Windows diag round 12: replace cmd /c invocation with Start-Process'
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
- tests/test_ci_workflow_matrix.py::TestWindowsDiagStepDoesNotGateTheJob::test_diag_invocation_is_wrapped_in_try_catch
- tests/test_ci_workflow_matrix.py::TestWindowsDiagStepDoesNotGateTheJob::test_diag_invocation_output_capture_is_unconditional
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Run 33480116817: round 11 WORKED up to a point -- all four breadcrumbs
printed ("fixture dir + pyproject.toml written", "git init + initial
commit done", "diag python file written", "about to invoke uv via
cmd /c"), then the step died ~1.3s later with exit 1 and NO further
output: the killer is the invocation line itself,

  $cmdOutput = & cmd /c $cmdLine 2>&1 | Out-String   (ci.yml:469)

(the "cmd /c returned" breadcrumb at :472 never printed).
$ErrorActionPreference='Continue' is active, so this is another pwsh
native-stream landmine, this time at the cmd boundary.

STOP fighting pwsh stream semantics. The SAME workflow's Windows Test
step already runs a child successfully on this exact runner with
Start-Process:

  $p = Start-Process -FilePath "uv" -ArgumentList ... -PassThru
       -RedirectStandardOutput $stdout -RedirectStandardError $stderr

Round 12: replace the cmd /c invocation with that proven pattern
(child = uv run --project $env:GITHUB_WORKSPACE python $diagPy, cwd at
the fixture via -WorkingDirectory), bounded Wait-Process at 290s, then
UNCONDITIONALLY (finally-style) Get-Content both redirect files and
print them, print the exit code via $p.ExitCode, and keep the
elapsed-time hang discriminator and exit-0-on-non-hang contract.
Wrap the whole invocation region in try/catch printing "invoke threw:
$_" so no failure mode is ever silent again. Update the matrix test's
assertions for the new invocation shape.
Scope: .github/workflows/ci.yml + tests/test_ci_workflow_matrix.py.