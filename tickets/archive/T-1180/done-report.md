## Done report

Made `make coverage` flake-tolerant end to end, per the ticket's three
failure modes (corrupt shim, 2x load-flake halts, stale-data combine
skip):

1. Serial rerun-once: a parallel-run pytest failure no longer halts the
   recipe. Failed tests are re-run exactly once with xdist parallelism
   disabled (`-n 0`, overriding `[tool.pytest.ini_options] addopts`'s
   baked-in `-n auto`) and scoped to `--last-failed`, appending onto the
   same coverage data (`--cov-append`). `combine`/`xml`/`frob check
   --stamp-coverage` now always run regardless of the (possibly still
   nonzero) rerun status; only a test still failing after the serial
   rerun fails the target (`exit $status` at the end of the recipe's
   shell block).
2. Stale-data cleanup: the existing `rm -f .coverage .coverage.*` at the
   top of the recipe doubles as the acceptance criterion's stale-file
   guard -- since the parallel pass and the serial rerun share ONE
   recipe invocation (rerun appends, never restarts), there is no window
   between them where a leftover file from an earlier, separate, aborted
   run could get silently combined alongside fresh data (the "2 of 7
   data files" incident).
3. Deflation floor before stamp: `stamp_coverage` (`frob.gates._coverage`)
   now refuses to write `.frob/coverage-stamp`/`frob-coverage.lock.json`
   at all (`Err(GateError.CoverageDeflated)`) when the coverage.xml it is
   about to stamp joins too small a fraction of known modules (TEST011's
   existing 0.5 `module_join_fraction` heuristic, promoted from a
   WARN-only advisory to a hard pre-stamp gate) -- but only above
   `_DEFLATION_MIN_KNOWN_MODULES` (20) known `.py` modules, since a tiny
   repo/fixture's near-zero join fraction is sample-size noise, not
   deflation.

CORRECTION mid-dispatch: the original dispatch note asked me to run
`make coverage` myself as live end-to-end evidence. That conflicts with
playbook 6b (a dispatched sub-agent cannot wait on a background
`make coverage` run) -- flagged by the coordinator and corrected. The
coordinator's guidance is followed here: T-1180 closes on the UNIT
evidence bound below (the deflation-floor and serial-rerun tests, which
directly exercise the acceptance criteria's own mechanics), and the live
full-suite `make coverage` validation is left to the coordinator, who
can wait on it.

What the in-dispatch (out-of-band, not claimed as this ticket's
evidence) attempts DID catch and fix, disclosed for the record:
- First `make coverage` attempt: `pytest: error: unrecognized arguments:
  -n` in the serial rerun stage -- `-p no:xdist` conflicts with
  `addopts`' baked-in `-n auto` once the xdist plugin is unloaded. Fixed
  by using `-n 0` instead (overrides the worker count, keeps the plugin
  loaded). Landed as its own follow-up commit.
- That same first attempt's failure list caught a REAL regression in an
  earlier version of the deflation floor: an unconditional floor broke
  13 existing tests that stamp tiny fixture coverage.xml files
  (`test_only_gates_passes_once_bound_and_tested`,
  `test_perf001_fixture_warns_but_check_exits_zero`,
  `test_repo_design_and_declarations_are_self_conformant`, and others).
  Fixed by adding `_DEFLATION_MIN_KNOWN_MODULES` (20) -- verified
  against all 13 affected tests individually before and after the fix.
- The four load-sensitive specimens named in the ticket (three strata
  self-model tests plus `test_serve_watch.py::TestWatchTick`'s tick
  tests) were re-verified to pass in isolation, confirming they are
  load-sensitive flakes, not real regressions, exactly as the ticket
  instructed.
- Neither attempt's `make coverage` run was allowed to run to
  completion/be waited on in-dispatch once the playbook-6b conflict was
  flagged -- the second (post `-n 0` fix) run was killed mid-flight per
  the coordinator's correction, and any partial `.coverage*`/
  `coverage.xml` artifacts it left were cleaned up. The coordinator owns
  running the real, complete `make coverage` and reporting the honest
  TEST005 count from it.

### Changed
```
 Makefile                    |  45 +++-
 design/frob.strata          |   1 +
 docs/modules/gates.md       |  13 +-
 frob-coverage.lock.json     | 624 ++++++++++++++++++++++++++++----------------
 src/frob/gates/__init__.py  | 121 +--------
 src/frob/gates/_coverage.py | 122 +++++++--
 src/frob/gates/_dup.py      | 148 +++++++++++
 src/frob/gates/_models.py   |   8 +
 tests/test_coverage.py      |  70 +++++
 tests/test_gates.py         |  64 ++++-
 tickets.md                  |  95 ++++++-
 11 files changed, 935 insertions(+), 376 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestCoverageLoad::test_stamp_coverage_refuses_below_deflation_floor` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageLoad::test_stamp_coverage_deflation_floor_skipped_below_min_known_modules` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestCoverageTargetFlakeTolerance::test_first_pass_failure_does_not_abort_the_recipe` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestCoverageTargetFlakeTolerance::test_rerun_is_serial_and_scoped_to_last_failed` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestCoverageTargetFlakeTolerance::test_combine_xml_stamp_run_unconditionally_after_the_rerun` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestCoverageTargetFlakeTolerance::test_target_exit_reflects_final_status_not_always_zero` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 0 error(s), 2518 warning(s), 496 waived
- error-findings: none (measured, zero errors)
