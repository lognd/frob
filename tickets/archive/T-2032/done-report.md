## Done report

Changed:
- src/frob/testing/_coverage_refresh.py::_strip_worker_count_flag (new)
- src/frob/testing/_coverage_refresh.py::_WORKER_COUNT_FLAGS (new)
- src/frob/testing/_coverage_refresh.py::_PYTEST_UNMEASURABLE_EXIT_CODES (new)
- src/frob/testing/_coverage_refresh.py::_retry_after_worker_crash (fixed)

Evidence:
- tests/test_coverage.py::TestWorkerCrashRetryArgvStripsWorkerCount::test_retry_argv_contains_neither_n_flag_nor_its_value
  (designated repro; FAILED_AT_PARENT at 090837ca9faed1053e4f7e08e15dcbbea40dde93,
  the test-only commit -- confirmed via `frob ticket evidence --check-repro
  --base-ref 090837ca9faed1053e4f7e08e15dcbbea40dde93`. Also watched it fail
  directly under plain pytest before the fix: AssertionError `assert '-n' not
  in ['pytest', '--cov=src/frob', '--cov-report=', '-n', '12', '-p', ...]`)
- tests/test_coverage.py::TestWorkerCrashRetryUnmeasurableExitReporting::test_retry_exit_4_is_not_reported_as_a_real_failure
  (FAILED_AT_PARENT confirmed the same way; observed pre-fix AssertionError:
  `'this is a REAL failure' is contained here` in the log message)
- tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_produces_coverage_xml_after_worker_crash_recovery
  (criterion 3, end-to-end through native_coverage_refresh: first parallel
  attempt matches the crash signature, serial retry succeeds, coverage.xml
  production path is reached)

All three pass post-fix (`uv run pytest tests/test_coverage.py -k "WorkerCrash
or worker_crash or TestNativeCoverageRefresh"` -> 14 passed, 0 failed).

Acceptance criterion 4 (other argv-mutating retry paths in this module):
searched the whole 1085-line src/frob/testing/_coverage_refresh.py for
`retry`/`respawn`/argv-splice patterns. `_retry_after_worker_crash` is the
ONLY retry path in the module -- one call site (`_pytest_outcome`), one
place that builds a derived argv from an existing one. None found, searched
1 module (the ticket's whole scope) end to end.

Filed: none -- no out-of-scope work discovered.

Gates: `uv run frob check --ticket T-2032 --only lint` clean for both scoped
files (0 ruff-check errors, 0 ruff-format diffs in
src/frob/testing/_coverage_refresh.py / tests/test_coverage.py; the run's 3
repo-wide errors and 120 warnings are all in files outside this ticket's
scope, pre-existing). `frob ticket evidence --check-repro` confirmed
FAILED_AT_PARENT for both new unit tests before designating/landing, per
playbook 7b's test-only-commit technique.

Not run: full unscoped `frob check`/`make coverage`/the whole
tests/test_coverage.py file in one pytest invocation -- both exceed the
foreground timeout budget (playbook 3b/3c); collection of the whole file
was verified clean instead (44 collected, 0 errors), and the relevant
classes were run directly and pass.

### Changed
```
 src/frob/testing/_coverage_refresh.py |  67 +++++++++++++++++++-
 tests/test_coverage.py                | 112 ++++++++++++++++++++++++++++++++++
 tickets/T-2032/ticket.md              |  24 +++++++-
 3 files changed, 199 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_coverage.py::TestWorkerCrashRetryArgvStripsWorkerCount::test_retry_argv_contains_neither_n_flag_nor_its_value` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestWorkerCrashRetryUnmeasurableExitReporting::test_retry_exit_4_is_not_reported_as_a_real_failure` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_produces_coverage_xml_after_worker_crash_recovery` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH103@src/frob/app/ticket_runner/_query.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2032/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2032/tests/unit/test_tickets_evidence_only_scope.py, PII012@src/frob/testing/_coverage_refresh.py, PRE001@tickets/T-2032
