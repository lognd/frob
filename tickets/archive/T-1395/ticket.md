---
id: T-1395
title: 'Coverage attribution still misses daemon and CLI-entry processes: serve/ and
  __main__.py remain 0.0%'
state: done
kind: bug
origin: human
created: '2026-08-01'
priority: high
blocked_by:
- T-1433
parent: null
tier: ticket
sprint: null
scope:
- src/frob/testing/_coverage_wait.py
- src/frob/serve/_socketd.py
- tests/unit/test_coverage_attribution_lock_t1395.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_coverage_attribution_lock_t1395.py
  reason: 'regression-lock evidence: assert the committed frob-coverage.lock.json
    (this ticket''s own re-verification artifact) keeps serve/__main__/daemon-adjacent
    modules non-zero, so a future regression back to the 0.0% daemon/CLI-entry attribution
    failure this ticket tracked is caught even though no code fix belongs in this
    ticket''s two scoped files'
  actor: logan
  at: '2026-08-03'
evidence:
- tests/unit/test_coverage_attribution_lock_t1395.py::TestCoverageAttributionLockStaysNonZero::test_t1395_named_modules_are_nonzero_in_committed_lock
- tests/unit/test_coverage_attribution_lock_t1395.py::TestCoverageAttributionLockStaysNonZero::test_no_module_reads_exactly_zero_in_committed_lock
designated_repro_test: null
acceptance:
- text: GIVEN a successful unscoped make coverage run WHEN the TEST005 report is read
    THEN src/frob/serve/** symbols exercised by the daemon tests report non-zero branch
    coverage
  evidence:
  - tests/unit/test_coverage_attribution_lock_t1395.py::TestCoverageAttributionLockStaysNonZero::test_t1395_named_modules_are_nonzero_in_committed_lock
  - tests/unit/test_coverage_attribution_lock_t1395.py::TestCoverageAttributionLockStaysNonZero::test_no_module_reads_exactly_zero_in_committed_lock
- text: GIVEN the same run WHEN src/frob/__main__.py::main is read THEN it reports
    non-zero branch coverage rather than 0.0%
  evidence:
  - tests/unit/test_coverage_attribution_lock_t1395.py::TestCoverageAttributionLockStaysNonZero::test_t1395_named_modules_are_nonzero_in_committed_lock
  - tests/unit/test_coverage_attribution_lock_t1395.py::TestCoverageAttributionLockStaysNonZero::test_no_module_reads_exactly_zero_in_committed_lock
threat: null
component: null
---
Measured on main 2026-08-01 after T-1235's subprocess-rc fix landed and make coverage completed green (exit 0, 851 files stamped, source_sha=de76e283).

T-1235's fix demonstrably worked for one class of process: modules that were pinned at 0.0% now report real numbers --
  src/frob/excludes.py::load_exclude_globs   6.7%  (was 0.0)
  src/frob/excludes.py::is_excluded         50.0%  (was 0.0)
  src/frob/doctor.py::scan_venv_shims        3.0%  (was 0.0)
  src/frob/doctor.py::verify_derived_state  50.0%  (was 0.0)

But two of the four module groups T-1235's own acceptance criterion names are STILL at exactly 0.0%:
  src/frob/serve/_leases.py::ResourceLeaseManager.{acquire,release,release_holder}
  src/frob/serve/_socketd.py::daemon_version
  src/frob/__main__.py::main
  src/frob/__main__.py::_SuggestingArgumentParser.error

These share a property the fixed modules do not: they execute in a daemon or CLI-entry process that the subprocess rc does not reach. The daemon is spawned by the socket server, and __main__ runs as the console-script entry -- neither inherits COVERAGE_PROCESS_START the way the pytest-spawned subprocesses do.

306 symbols repo-wide remain at exactly 0.0%, so this is not a rounding artifact.

Related signal worth checking while here: load_coverage reports module_join_fraction=0.53, i.e. only about half of mapped modules join to the graph. T-1236's deflation guard exists for exactly this shape.

This ticket exists because T-1235 cannot honestly close until serve/ and __main__.py attribute -- its criterion names them explicitly, and binding evidence to a half-satisfied criterion would be the false-close this queue has been bitten by before.

## Failure log
- 2026-08-01 attempt 1: Investigated exhaustively (empirical repros of both a real subprocess-spawned daemon and python -m frob CLI entry under the exact Makefile-generated absolute-path subprocess rc): the COVERAGE_PROCESS_START/concurrency mechanism already attributes both process classes correctly in isolation, so this is not a T-1235-style env-inheritance defect confined to src/frob/testing/_coverage_wait.py or src/frob/serve/_socketd.py -- FROB_DAEMON defaults off so _worktree_lock's daemon-lease path never even runs during make coverage, ruling that out too. Filed T-1397 for a real but unrelated Loss-A-shaped bug found in coverage-fast (out of scope: Makefile). The likely real root cause is the already-documented xdist worker-crash/stuck-test data-loss class or the module_join_fraction graph-mapping gap (T-1236), neither fixable from this ticket's two scoped files; forcing an unverifiable change here would violate the do-not-force rule.