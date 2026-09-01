## Done report

Round 10 = instrumentation, not another guess. Round 9's fixes
(ErrorActionPreference=Continue, commitless-fixture empty commit) were
verified correctly placed by run 33466891764, yet the step still died
at ~1.6s printing only "frob: interrupted" with none of the script's
own Write-Host lines reached -- neither of round 9's fixes explains
this failure mode by itself, so this round adds instrumentation
instead of another targeted guess:

1. Write-Host breadcrumbs before/after every major block (fixture
   setup, diag-file write, invoke, cmd-return) so whichever marker is
   last localizes the kill point.
2. The uv/python child now runs through `cmd /c "... 1>diag.out
   2>diag.err & echo child-exit=%ERRORLEVEL%"` instead of as a native
   pwsh command, removing pwsh's own native-command stream/signal
   handling from the picture entirely; both streams are captured to
   files that get echoed back with Get-Content regardless of how the
   step itself ends.
3. The diag python script's first statement (before even `import
   faulthandler`) prints a flushed liveness marker, and the
   frob.__main__.main() call is wrapped in try/except BaseException
   printing repr()+traceback before re-raising, so "interrupted" gets
   a stack instead of nothing.
4. The elapsed-time discriminator and 0/1 exit-code contract are
   unchanged.

Evidence: tests/test_ci_workflow_matrix.py::TestWindowsDiagStepDoesNotGateTheJob's
3 new tests (liveness marker, BaseException wrapping, breadcrumbs) plus
2 rewritten pre-existing assertions (--project pin now escaped inside
the cmd string; the stderr-redirect check now targets the pwsh-level
cmd /c invocation instead of a bare uv run line, since the uv/python
invocation moved inside a cmd string) and one rewritten
still-scans-the-fixture test. Full tests/test_ci_workflow_matrix.py:
18/18 pass.

Filed: none. T-3620 (opaque "frob: interrupted" on commitless repos)
stays open and is not directly implicated here since round 9 already
gave the fixture a commit -- if round 10's stack trace (once a real
windows run captures it) shows the same underlying frob code path,
note it there.

### Changed
```
 .github/workflows/ci.yml         |  54 ++++++++++++--
 tests/test_ci_workflow_matrix.py | 156 ++++++++++++++++++++++++++-------------
 tickets/T-3624/ticket.md         |   4 +
 3 files changed, 157 insertions(+), 57 deletions(-)
```

### Evidence
- `tests/test_ci_workflow_matrix.py::TestWindowsDiagStepDoesNotGateTheJob::test_diag_python_prints_liveness_marker_before_anything_else` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsDiagStepDoesNotGateTheJob::test_diag_python_wraps_main_call_in_baseexception_handler` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsDiagStepDoesNotGateTheJob::test_diag_step_has_breadcrumbs_around_every_major_block` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 27 error(s), 4142 warning(s), 900 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, ARCH103@src/frob/tickets/_leases.py, COV003@tests/gates_suite/test_compliance.py, COV003@tests/gates_suite/test_coverage.py, COV003@tests/gates_suite/test_debt.py, COV003@tests/gates_suite/test_doc.py, COV003@tests/gates_suite/test_fix_engine.py, COV003@tests/gates_suite/test_invariant.py, COV003@tests/gates_suite/test_prework.py, COV003@tests/gates_suite/test_protocol.py, COV003@tests/gates_suite/test_run.py, COV003@tests/gates_suite/test_sys.py, COV003@tests/gates_suite/test_test_gate.py, COV003@tests/gates_suite/test_tick.py, COV003@tests/gates_suite/test_waive.py, COV003@tests/gates_suite/test_wire.py, COV003@tests/test_ci_workflow_matrix.py, COV007@src/frob/strata/_capacity.py, DEPR006@frob-deprecated-baseline.lock.json, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/app/_config_external.py, PRE001@tickets/T-3624, REL001@src/frob/__init__.py, TEST001@src/frob/strata/_models.py, WAIVE011@frob-ratchet.lock.json
