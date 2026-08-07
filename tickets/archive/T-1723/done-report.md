## Done report

frob:no-behavior-change reason="all fixes are behavior-preserving: two pure function-boundary splits (spawn/supervise/reap and worker-crash-retry seams, same control flow just given names) and one waiver comment on an env-var read that carries a plain numeric deadline, not a secret -- no runtime behavior changed, so the designated repro test correctly PASSES at main rather than failing there"

Fixed all 3 error identities (ARCH001 x2, ARCH103 x2, SEC110 x1) in
src/frob/testing/_coverage_refresh.py, introduced by T-1677's land.

Split along real seams, not just to get under the line-count threshold:

- `_kill_process_group` (ARCH103, mixed platform I/O) split into
  `_kill_process_group_windows`/`_kill_process_group_posix` along the
  platform branch that was already there; the orchestrator now just
  picks a branch and always reaps at the end regardless of which ran.
- `_spawn_with_watchdog` (ARCH001: 102 lines; ARCH103: mixed I/O/
  formatting/branching) split into `_spawn_watchdog_process` (the spawn
  seam: tempfile + Popen, platform-branched, OSError handling) and
  `_supervise_watchdog_process` (the supervise seam: the poll loop
  enforcing both deadlines). `_spawn_with_watchdog` is now a thin
  orchestrator that sequences the two and owns the temp log file's
  lifetime end to end.
- `_pytest_outcome` (ARCH001: 84 lines) split by extracting the
  worker-crash serial-retry logic into `_retry_after_worker_crash`
  (returns the exit code to file the run's data under: the retry's own
  code if it completed, the original code unchanged if the retry itself
  failed to spawn) -- the worker-crash RECOVERY concern is now a named
  seam separate from the outer classify-and-report logic.
- SEC110 at `_watchdog_config_from_env`'s `_read` closure: looked at
  what it actually reads -- `FROB_COVERAGE_WALLCLOCK_DEADLINE_S`/
  `FROB_COVERAGE_NO_PROGRESS_DEADLINE_S`, both plain numeric seconds
  overrides for the watchdog's own deadlines, never a secret. Added
  `frob:waive SEC110 reason="..."`, the same inline pattern already used
  for the identical false-positive shape at
  src/frob/app/telemetry.py:51/399 (opt-out env flags).

Changed:
- src/frob/testing/_coverage_refresh.py::_kill_process_group_windows (new)
- src/frob/testing/_coverage_refresh.py::_kill_process_group_posix (new)
- src/frob/testing/_coverage_refresh.py::_kill_process_group (split caller)
- src/frob/testing/_coverage_refresh.py::_spawn_watchdog_process (new)
- src/frob/testing/_coverage_refresh.py::_supervise_watchdog_process (new)
- src/frob/testing/_coverage_refresh.py::_spawn_with_watchdog (split caller)
- src/frob/testing/_coverage_refresh.py::_retry_after_worker_crash (new)
- src/frob/testing/_coverage_refresh.py::_pytest_outcome (split caller)
- src/frob/testing/_coverage_refresh.py::_watchdog_config_from_env (SEC110 waiver)

Evidence: 6 existing pytest node ids in tests/test_coverage.py that
directly exercise the split functions (TestSpawnWithWatchdog's 3 tests
for the spawn/supervise/reap seams, TestPytestOutcomeWorkerCrashRecovery's
3 tests for the retry seam).

Verification:
- `uv run ty check src/frob/testing/_coverage_refresh.py` -- all checks passed.
- `uv run ruff check`/`ruff format --check` on the same file -- both clean.
- `uv run pytest tests/test_coverage.py -q` -- 32 passed.
- `uv run frob check --only archgate` -- 0 errors for this file (was 4).
- `uv run frob check --only secrets` -- 0 errors for this file (was 1).
- `uv run frob check --land-parity` -- clean, 0 unscoped errors. This is
  main's ENTIRE error floor cleared -- the first zero reading this session.

Filed: none.
Gates: frob check --land-parity clean, 0 unscoped errors. One waiver
added (SEC110, reasoned, same convention as existing precedent).

### Changed
```
 tickets.md | 18 ++++++++++++++----
 1 file changed, 14 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_coverage.py::TestSpawnWithWatchdog::test_wall_clock_deadline_kills_and_reports` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestSpawnWithWatchdog::test_no_progress_deadline_kills_a_silent_hang` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestSpawnWithWatchdog::test_killed_process_group_leaves_no_surviving_children` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestPytestOutcomeWorkerCrashRecovery::test_crash_signature_triggers_one_serial_retry` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestPytestOutcomeWorkerCrashRecovery::test_crash_signature_with_failing_retry_stays_degraded` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestPytestOutcomeWorkerCrashRecovery::test_ordinary_red_suite_is_not_classified_as_worker_crash` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 0 error(s), 148 warning(s), 718 waived
- error-findings: none (measured, zero errors)
