## Done report

Changed:
- .github/workflows/ci.yml (windows-latest Test step: `-v --full-trace` replacing `-q`; T-3560 comment block)
- tests/conftest.py (`_install_sigbreak_faulthandler`, wired into `pytest_configure`)

DELIVERABLE 1 only (instrumentation land), per the coordinator's brief:
the windows-latest Test step now runs pytest with `-v --full-trace`
instead of `-q` so the interrupted test is named and its traceback is
complete, and `tests/conftest.py` registers `faulthandler` on
`SIGBREAK` (win32-only, guarded no-op elsewhere) so a console ctrl
event dumps every thread's stack to stderr the instant it arrives,
independent of whether it turns into the `KeyboardInterrupt` pytest
catches. Both are explicitly commented as TEMPORARY T-3560 diagnostics
to be reverted in the same land that fixes (or documents) the named
root cause. No behavior change on linux/macos or off-CI runs -- the
faulthandler registration is a guarded no-op there, and `-v
--full-trace` only changes pytest's own output verbosity on the
windows-latest leg.

Evidence:
- tests/unit/test_conftest_stackdump.py::TestSelfScanHeavyGrouping::test_self_scan_heavy_tests_share_one_xdist_group (pytest node id, verified passing -- conftest.py still imports/collects cleanly with the new signal import and helper)
- tests/unit/test_release_workflow_gate.py::TestReleaseWorkflowNoAutomaticTrigger::test_only_workflow_dispatch_trigger (pytest node id, verified passing -- ci.yml's existing structural assertions are unaffected by the Test-step arg change)

Filed: none (this ticket itself, T-3560, was filed per the coordinator's brief; deliverable 2, the actual root-cause fix + instrumentation revert, is explicitly deferred to a follow-up land per the ticket body)

Gates: `uv run pytest -p no:xdist tests/unit/test_conftest_stackdump.py`
(24 passed) and `tests/unit/test_release_workflow_gate.py` (21 passed)
both clean. Scoped `frob check --ticket T-3560 --only affect_drift
--only coverage --only fmt` clean on this ticket's own touched-set
concerns (no AFFECT001/COV002/TODO001/FMT001 against either touched
file); repo-wide FAIL lines (WAIVE, DRIFT, COV007 on unrelated files)
are pre-existing per the run's own scope note.
