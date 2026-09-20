## Done report

Changed:
.github/workflows/ci.yml (windows Test step Start-Process ArgumentList: added "-rA","--tb=short")
tests/test_ci_workflow_matrix.py::TestWindowsDiagStepDoesNotGateTheJob.test_win32_test_step_surfaces_failure_tracebacks

Evidence: tests/test_ci_workflow_matrix.py -p no:xdist -q -> 68 passed, 0 failed (includes the new test above, bound via frob:tests .github/workflows/ci.yml on the new test)

Diagnosis (Step 1, local Linux repro in worktree, deleted before commit):
- Created tests/test__tb_probe_DELETEME*.py (assert False probes), ran under the
  project's real addopts (-n auto --dist=loadgroup --timeout=120/thread from
  pyproject). Plain `-q` alone ALREADY printed the full FAILURES section with
  tracebacks, for both a single probe and 5 probes spread across xdist workers.
  `-rA --tb=short` and `-n 2 --dist=loadgroup -rA --tb=short` also printed full
  tracebacks. The conftest.py SUITE-RESULT reporter (tests/conftest.py) does not
  suppress pytest's own FAILURES section in any of these scenarios -- it only
  hard-exits (os._exit) on stall/total-budget-exceeded paths, not on a clean full
  completion, so it is not implicated as blocking the ubuntu/macos/win32-isolated
  case.
- This means the local (Linux) evidence could not reproduce the win32-full-suite-
  only symptom exactly -- the trigger is plausibly Windows/Start-Process/log-
  capture specific (e.g. the PowerShell Start-Process + Get-Content redirection
  path, or a worker being killed mid-run only under the slower/larger win32 full
  suite) rather than a `-q`/xdist default suppressing the section outright. Per
  the ticket's own decision tree ("if a flag set works [locally], add exactly
  those flags"), `-rA --tb=short` reliably prints full tracebacks locally under
  the real addopts, so it was added to the win32 Test step as the diagnostic
  verbosity increase. This is a best-effort fix given the platform-specific
  reproduction gap -- flagging this explicitly rather than claiming the exact CI
  mechanism was confirmed.

Filed: none

Gates: `uv run frob check --ticket T-3785` -- 0 errors attributable to
.github/workflows/ci.yml or tests/test_ci_workflow_matrix.py (only DOCARCH001
warnings and DUP001 notes on the new test, both non-blocking; pass counts
above). Full-run FAIL rows (ruff-format, ty, DRIFT, LANG, PRE, REF) are
pre-existing repo-wide findings unrelated to the two touched files (verified:
`ruff format --check .`'s 3 "Would reformat" files are
src/frob/gates/_debt_deprecated.py, tests/test_hook_frob_suggest.py,
tests/unit/test_conftest_stackdump.py -- none touched by this ticket; no error
diagnostic in the JSON check output names ci.yml or test_ci_workflow_matrix.py).
frob:waive BUG002 reason="CI-config diagnostic verbosity change (win32 pytest
-rA --tb=short); no runtime behavior/repro, no pass/fail semantic change"
recorded on the ticket body.

### Changed
```
 src/frob/process/_guard.py         | 39 ++++++++++++++++++++++++++++++++++----
 tests/unit/test_process_guard.py   | 23 ++++++++++++++++++++++
 tickets/T-3797/ticket.md           | 14 ++++++++++++--
 tickets/T-3802/ticket.md | 28 +++++++++++++++++++++++++++
 4 files changed, 98 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/unit/test_process_guard.py::TestGuardedSubprocessRun::test_missing_binary_returns_err_spawn_failed_never_raises` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 4344 warning(s), 925 waived
- error-findings: none (measured, zero errors)
