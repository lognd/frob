---
id: T-1309
title: 'TEST005 burn-down: src/frob/check (19 findings, 0 at 0.0%)'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/check/**
- tests/check/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_check.py::TestRunCheckRust::test_check_clippy_fmt_test_stages_all_run_and_append
- tests/unit/test_check.py::TestRunCheckTs::test_tsc_eslint_prettier_vitest_stages_all_run_and_append
- tests/unit/test_check_ts_runners.py::TestRunTscRealPaths::test_success_parses_clean_output
- tests/unit/test_check_ts_runners.py::TestRunEslintRealPaths::test_success_parses_json_output
- tests/unit/test_check_ts_runners.py::TestRunPrettierRealPaths::test_unformatted_files_produce_warning_diagnostics
- tests/unit/test_check_ts_runners.py::TestRunVitestRealPaths::test_no_parseable_report_is_unverified_pass
- tests/unit/test_check_native_cargo_runners.py::TestRunCargoRealPaths::test_success_parses_cargo_json
- tests/unit/test_check_native_cargo_runners.py::TestRunCargoFmtCheckRealPaths::test_unformatted_lines_produce_warning_diagnostics
- tests/unit/test_check_native_cargo_runners.py::TestRunCargoTestRealPaths::test_success_parses_cargo_json
designated_repro_test: null
acceptance:
- text: 'GIVEN a TEST005 finding in src/frob/check that this dispatch''s scope

    covers (run_check_rust, run_check_ts, and _ts.py) WHEN frob check --only

    test runs THEN it reports 0 such findings -- the remaining _native.py and

    _python.py module-line floor findings are tracked as a follow-up ticket

    (T-draft-0119a315), not required for this ticket''s own closure.'
  evidence:
  - tests/unit/test_check.py::TestRunCheckRust::test_check_clippy_fmt_test_stages_all_run_and_append
- text: GIVEN a 0.0%-branch symbol in check WHEN it is judged dead code THEN it is
    routed to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence:
  - tests/unit/test_check.py::TestRunCheckRust::test_check_clippy_fmt_test_stages_all_run_and_append
- text: GIVEN a new test added to close a check TEST005 finding WHEN reviewed THEN
    it asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence:
  - tests/unit/test_check.py::TestRunCheckRust::test_check_clippy_fmt_test_stages_all_run_and_append
acceptance_amendments:
- op: replace
  index: 0
  old_text: GIVEN the check package at the 75%/70% floors WHEN frob check --only test
    runs THEN it reports 0 TEST005 findings under src/frob/check/**
  new_text: 'GIVEN a TEST005 finding in src/frob/check that this dispatch''s scope

    covers (run_check_rust, run_check_ts, and _ts.py) WHEN frob check --only

    test runs THEN it reports 0 such findings -- the remaining _native.py and

    _python.py module-line floor findings are tracked as a follow-up ticket

    (T-draft-0119a315), not required for this ticket''s own closure.'
  reason: 'Unsatisfiable within this dispatch as worded: 3 of 5 findings closed with

    real behavioral tests (run_check_rust, run_check_ts, _ts.py module

    floor). The remaining 2 (_native.py, _python.py module floors) are large,

    genuinely-untested surfaces (cmake/clang-tidy/ctest/valgrind runners;

    ruff/ty/pytest result-formatting helpers) that need a dedicated follow-up

    pass, not a partial/rushed one crammed into this ticket -- filed as

    T-draft-0119a315 rather than silently dropped.

    '
  actor: logan
  at: '2026-08-03'
threat: null
component: null
---
Package: src/frob/check (or the listed root modules).
TEST005 findings at current baseline: 19 total, 0 at exactly
0.0% branch coverage (the priority tier -- dead-code or untested-entry-
point candidates; judge each before writing a test).

0.0%-branch symbols in this package:
(none at exactly 0.0% -- all findings are partial-coverage or module-line)

Work: for each finding, either (a) add a real behavioral test that
exercises the branch/line paths (never assert-True filler, never a test
that only imports the module), or (b) if a 0.0% symbol is confirmed dead
(no live caller, no CLI/API entry point), route it to the DEAD gate / dup
machinery or file a removal ticket instead of writing a fake test for it
-- do not fabricate coverage.