## Done report

(Resumed from a prior stalled agent.)

A prior agent left 5 of 11 tickets partially repointed (T-1335, T-1353,
T-1363, T-1373, T-1426) before stalling. Re-verification found T-1363 and
T-1426 fully and correctly repointed (0 remaining COV003 hits); T-1335,
T-1353, and T-1373 were each only PARTIALLY repointed -- some evidence ids on
those tickets still cited deleted `test_makefile_coverage.py` nodes. This
report covers finishing all 6 originally-assigned tickets (T-1205, T-1235,
T-1362, T-1397, T-1433, T-1526) plus completing the 3 that were left
incomplete (T-1335, T-1353, T-1373).

### Per-ticket old-node -> new-node -> shared claim (acceptance criterion 2)

- **T-1335** (2 of 3 already-done nodes were fine; these 3 needed repointing):
  - `TestStampFailurePropagation::test_stamp_failure_after_green_suite_fails_the_recipe`
    -> `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_failure_exits_1`.
    Claim: a failing stamp-coverage step must fail the whole recipe nonzero,
    naming the failure (`_run_stamp_coverage` logs `"stamp-coverage failed: %s"`
    and `sys.exit(1)`).
  - `TestStampFailurePropagation::test_green_suite_and_green_stamp_still_exits_zero`
    -> `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_mode_calls_stamp_and_returns`.
    Claim: the unchanged success path still completes normally.
  - `TestCoverageXmlIgnoreErrors::test_combine_then_xml_survives_a_stale_fixture_path`
    -> `tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists`.
    Claim: `coverage xml` always runs with `-i`/`--ignore-errors` so a
    torn-down source path does not abort the run (T-1320); `native_coverage_
    refresh`'s own xml call (`src/frob/testing/_coverage_refresh.py`) passes
    `-i` unconditionally, per its own T-1320 comment.

- **T-1353** (2 of 4 nodes were already repointed by the prior agent; these 2
  needed finishing): same two `TestStampFailurePropagation` repoints as
  T-1335 above, same shared claims.

- **T-1362**: `TestCoverageXmlIgnoreErrors::test_combine_then_xml_survives_a_stale_fixture_path`
  -> `tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists`.
  Same `-i`/ignore-errors claim as above.

- **T-1373** (2 of 3 nodes were already fine; 1 needed repointing): same
  `test_combine_then_xml_survives_a_stale_fixture_path` repoint, same claim.

- **T-1433**:
  - `TestSerialRerunHasABoundedDeadline::test_both_serial_reruns_are_wrapped_in_a_bounded_timeout`
    -> `tests/test_coverage.py::TestSpawnWithWatchdog::test_wall_clock_deadline_kills_and_reports`.
    Claim: a subprocess the coverage recipe spawns is wrapped in a bounded
    wall-clock deadline that kills a wedged/never-finishing child instead of
    hanging forever (T-1433's own field incident). The bounded-timeout
    mechanism moved from Makefile `timeout -k 30 $(COVERAGE_RERUN_DEADLINE)`
    text into `native_coverage_refresh`'s `_spawn_with_watchdog` (T-1677),
    which wraps every subprocess this module spawns, including reruns.
  - `TestSerialRerunHasABoundedDeadline::test_timeout_wrapping_kills_a_wedged_child_instead_of_hanging`
    -> `tests/test_coverage.py::TestSpawnWithWatchdog::test_no_progress_deadline_kills_a_silent_hang`.
    Claim: ground-truth proof the wrapping mechanism actually kills a wedged
    child (a silent hang, the T-1433 futex_wait shape) within a bounded
    window, not decorative recipe text.

- **T-1526**: `TestCoverageXmlIgnoreErrors::test_coverage_xml_invocations_pass_ignore_errors`
  -> `tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists`.
  Same `-i`/ignore-errors claim; `coverage-fast` now delegates entirely to
  `native_coverage_refresh` per this same ticket's own rewrite, so there is
  no separate Makefile-side xml invocation left to test.

### Orphaned citations with NO surviving equivalent (acceptance criterion 3)

10 of the 20 remaining COV003 findings have no surviving equivalent and were
left un-repointed, reported here explicitly rather than repointed to an
approximation:

- **T-1205**: `TestCoverageFastUsesAbsoluteSubprocessRc::test_coverage_fast_uses_the_shared_absolute_rc`
  (cited twice, acceptance[0] and [3]).
- **T-1235**: `TestSubprocessRcIsAbsoluteAndConcurrencyAware::test_rc_uses_absolute_source_and_data_file`,
  `::test_rc_declares_multiprocessing_and_sigterm`, `::test_rc_remaps_paths_back_to_source`,
  `::test_pyproject_declares_concurrency_and_sigterm`.
- **T-1397**: `TestCoverageFastUsesAbsoluteSubprocessRc::test_coverage_fast_never_points_at_pyproject_toml`,
  `::test_coverage_fast_uses_the_shared_absolute_rc`, `::test_rc_file_target_is_shared_not_duplicated`.
- **T-1526**: `TestCoverageFastUsesAbsoluteSubprocessRc::test_coverage_fast_uses_the_shared_absolute_rc`,
  `::test_coverage_fast_still_rebuilds_natives_first`.

Why: all ten assert on the `.frob/coverage-subprocess.rc` generation
mechanism and/or `coverage-fast:`'s own inline recipe text. That generation
step itself was REMOVED, not migrated -- Makefile:298-306's own comment
discloses this explicitly: "neither this path nor `coverage-fast:` ...
generates `.frob/coverage-subprocess.rc`/sets `COVERAGE_PROCESS_START`, so a
test that spawns `frob` ... as a real subprocess is not separately
coverage-instrumented the way the old ~40-line recipe's manual rc ...
measured it ... a follow-up to re-add subprocess-coverage measurement to
`native_coverage_refresh` itself is real, tracked work." No test anywhere in
the current suite asserts this rc-generation/absolute-path/concurrency
behavior because the behavior itself is gone, by deliberate, disclosed
design choice (not by T-2240's own retirement) -- there is nothing honest to
repoint these ten citations to. A smaller honest repointing (18 of 28 ->
10 of 28 now resolved) beats a complete-looking one built on fabricated
citations.

### MUST-STILL-PASS control (acceptance criterion 4)

`tests/unit/test_makefile_coverage.py` is unchanged by this ticket (verified:
`git diff main -- tests/unit/test_makefile_coverage.py` is empty). Unscoped
`frob check --json` (`FROB_ALLOW_FULL_CHECK=1`, chunked full pass, all ~45
gate families ran, `gate-summary` present both times -- not a
budget-truncated read):

- Before (measured 2026-08-16, this ticket's own original measurement): 28
  `gate:COV:COV003` findings naming `tests/unit/test_makefile_coverage.py`,
  59 total errors.
- After (this session): 10 `gate:COV:COV003` findings (all 10 the orphaned,
  unrepointable set above), 53 total errors.

Floor dropped by exactly 18 -- the number of findings actually cleared, no
more and no less; the remaining 10 are the honestly-reported unrepointable
set, not a truncation artifact.

### No production code path changes (acceptance criterion 5)

Confirmed: `git diff main --stat` for this ticket's commits touches only
`tickets/archive/**/ticket.md` and `tickets/T-2256/ticket.md` -- no `src/`
change.

### Changed

Evidence rebinds (`frob ticket evidence --replace --archived`) on
`tickets/archive/T-1335`, `tickets/archive/T-1353`, `tickets/archive/T-1362`,
`tickets/archive/T-1373`, `tickets/archive/T-1433`, `tickets/archive/T-1526`;
plus `tickets/T-2256/ticket.md` (this ticket's own evidence and Done report).
T-1205/T-1235/T-1397/T-1526's remaining orphaned citations were left
untouched (reported above, not repointed).

### Filed

None. (T-2255, the guard fix that should have prevented this class, was
already filed before this ticket started and is out of this ticket's scope.)
