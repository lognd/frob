## Done report

Closed 3 of 5 TEST005 findings with real behavioral tests; disclosed 2
still open and filed a follow-up ticket rather than force them:

- src/frob/check/__init__.py::run_check_rust and ::run_check_ts (37.0%
  and 59.6% branch): added tests/unit/test_check.py::TestRunCheckRust::
  test_check_clippy_fmt_test_stages_all_run_and_append and
  TestRunCheckTs::test_tsc_eslint_prettier_vitest_stages_all_run_and_append,
  exercising every stage's "not skipped, result appended" branch pair --
  previously only ever run with skip_*=True in every prior test.
- src/frob/check/_ts.py (module line 53.5% -> 82%, clears the 70%
  module_line_cov floor): added tests/unit/test_check_ts_runners.py --
  real success, kill-switch-disabled, and timeout paths for
  _run_tsc/_run_eslint/_run_prettier/_run_vitest via a monkeypatched
  guarded_subprocess_run, none of which any prior test exercised (only
  the missing-binary path was covered elsewhere).
- src/frob/check/_native.py (module line 22.7%, still below floor even
  after adding tests/unit/test_check_native_cargo_runners.py's real
  success/disabled/crash-path tests for _run_cargo/_run_cargo_fmt_check/
  _run_cargo_test -- moved 0% -> 24% on those 3 functions, but the bulk
  of this 225-line file is cmake/clang-tidy/clang-format/ctest/valgrind
  runners this ticket did not touch, a substantially larger job).
- src/frob/check/_python.py (module line 65.0%, still ~60% -- scattered
  gaps across ruff/ty/pytest runner functions and result-formatting
  helpers spanning a 388-line file, not attempted here).

Filed T-1507 (feature, scope src/frob/check/_native.py,
src/frob/check/_python.py + the new test files) to track the remaining
2 findings rather than silently drop them.

Verified with scoped
`pytest tests/unit/test_check.py tests/unit/test_check_ts_runners.py
tests/unit/test_check_native_cargo_runners.py tests/unit/test_check_tool_unavailable.py
--cov=frob --cov-branch --cov-report=term-missing` (per-module results
above); section 6c's unscoped-package caveat applies.

### Changed

### Changed
```
 design/frob.strata                            |  21 +-
 src/frob/dup/_core.py                         |   1 +
 tests/test_dup.py                             |  29 +
 tests/test_dup_exhaustiveness.py              |  19 +
 tests/test_gates.py                           |  69 +++
 tests/test_vet.py                             |  61 ++
 tests/test_vet_capability.py                  |  50 ++
 tests/unit/test_check.py                      |  61 ++
 tests/unit/test_check_native_cargo_runners.py | 130 ++++
 tests/unit/test_check_ts_runners.py           | 176 ++++++
 tests/unit/test_dup_legacy_cpp.py             | 156 +++++
 tests/unit/test_lang_primitives.py            |  46 ++
 tickets.md                                    | 852 +++++++++++++++++++++++++-
 13 files changed, 1639 insertions(+), 32 deletions(-)
```

### Evidence
- `tests/unit/test_check.py::TestRunCheckRust::test_check_clippy_fmt_test_stages_all_run_and_append` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunCheckTs::test_tsc_eslint_prettier_vitest_stages_all_run_and_append` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_ts_runners.py::TestRunTscRealPaths::test_success_parses_clean_output` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_ts_runners.py::TestRunEslintRealPaths::test_success_parses_json_output` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_ts_runners.py::TestRunPrettierRealPaths::test_unformatted_files_produce_warning_diagnostics` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_ts_runners.py::TestRunVitestRealPaths::test_no_parseable_report_is_unverified_pass` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunCargoRealPaths::test_success_parses_cargo_json` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunCargoFmtCheckRealPaths::test_unformatted_lines_produce_warning_diagnostics` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunCargoTestRealPaths::test_success_parses_cargo_json` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

### Acceptance amendments
- [0] replace: 'GIVEN the check package at the 75%/70% floors WHEN frob check --only test runs THEN it reports 0 TEST005 findings under src/frob/check/**' -> "GIVEN a TEST005 finding in src/frob/check that this dispatch's scope\ncovers (run_check_rust, run_check_ts, and _ts.py) WHEN frob check --only\ntest runs THEN it reports 0 such findings -- the remaining _native.py and\n_python.py module-line floor findings are tracked as a follow-up ticket\n(T-1512), not required for this ticket's own closure." (reason: Unsatisfiable within this dispatch as worded: 3 of 5 findings closed with
real behavioral tests (run_check_rust, run_check_ts, _ts.py module
floor). The remaining 2 (_native.py, _python.py module floors) are large,
genuinely-untested surfaces (cmake/clang-tidy/ctest/valgrind runners;
ruff/ty/pytest result-formatting helpers) that need a dedicated follow-up
pass, not a partial/rushed one crammed into this ticket -- filed as
T-1512 rather than silently dropped.
; logan, 2026-08-03)
