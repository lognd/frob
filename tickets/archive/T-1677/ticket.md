---
id: T-1677
title: 'frob coverage can hang forever: no wall-clock deadline, no no-progress watchdog'
state: done
kind: bug
origin: human
created: '2026-08-06'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/testing/_coverage_refresh.py
- tests/test_coverage.py
- docs/modules/testing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/testing/_coverage_refresh.py
  reason: the wall-clock/no-progress watchdog and worker-crash detection this ticket
    asks for live entirely inside native_coverage_refresh's pytest-subprocess call
    path
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/test_coverage.py
  reason: the wall-clock/no-progress watchdog and worker-crash detection this ticket
    asks for live entirely inside native_coverage_refresh's pytest-subprocess call
    path
  actor: logan
  at: '2026-08-06'
- op: add
  glob: docs/modules/testing.md
  reason: the wall-clock/no-progress watchdog and worker-crash detection this ticket
    asks for live entirely inside native_coverage_refresh's pytest-subprocess call
    path
  actor: logan
  at: '2026-08-06'
evidence:
- tests/test_coverage.py::TestSpawnWithWatchdog::test_normal_completion_returns_exit_code_and_output
- tests/test_coverage.py::TestSpawnWithWatchdog::test_nonzero_exit_still_returns_ok_with_output
- tests/test_coverage.py::TestSpawnWithWatchdog::test_wall_clock_deadline_kills_and_reports
- tests/test_coverage.py::TestSpawnWithWatchdog::test_no_progress_deadline_kills_a_silent_hang
- tests/test_coverage.py::TestSpawnWithWatchdog::test_killed_process_group_leaves_no_surviving_children
- tests/test_coverage.py::TestPytestOutcomeWorkerCrashRecovery::test_crash_signature_triggers_one_serial_retry
- tests/test_coverage.py::TestPytestOutcomeWorkerCrashRecovery::test_crash_signature_with_failing_retry_stays_degraded
- tests/test_coverage.py::TestPytestOutcomeWorkerCrashRecovery::test_ordinary_red_suite_is_not_classified_as_worker_crash
- tests/test_coverage.py::TestNativeCoverageRefreshAbort::test_watchdog_abort_skips_xml_and_stamp_and_records_provenance
- tests/test_coverage.py::TestNativeCoverageRefresh::test_refused_spawn_is_err
designated_repro_test: null
threat: null
component: null
---
Field incident 2026-08-06, and the direct cause of a FIVE HOUR stall in the drain drive.

'frob coverage --full' reached 99% of test execution and then hung. The controller pytest process stayed alive and idle for 5h04m; its last log write was at the 5-minute mark. Diagnosis at kill time: one child was a defunct zombie, and a surviving xdist worker was blocked in futex_wait_queue. The controller waits on a worker that will never answer, forever. Nothing in the process tree ever times out:

- pytest's --timeout=120 applies to an individual TEST, not to a controller blocked in the xdist scheduler, so it never fired.
- native_coverage_refresh calls guarded_subprocess_run with no timeout at all.
- The 'nothing has been written to the log in 5 hours' condition is trivially detectable and nothing looks at it.

The symptom is indistinguishable from slow progress: the process is alive, the log's last line is a normal progress line, exit code is pending. An operator polling for completion waits indefinitely. That is exactly what happened -- the drive made no forward progress on measurement for five hours while three agents' work sat unlanded.

This is the resilience that src/frob/testing/_coverage_refresh.py's own module docstring discloses as deliberately NOT ported from the Makefile recipe: its xdist-crash serial-rerun recovery and the COVERAGE_RERUN_DEADLINE/COVERAGE_XDIST_DEADLINE knobs. The disclosure was honest, but the consequence is a coverage path that can hang forever, and 'make coverage' is being removed (T-1382), so the shell-side fallback is going away.

Work:
1. A hard wall-clock deadline on the pytest subprocess. Exceeded = kill the process GROUP (a plain kill leaves the workers), report explicitly, keep whatever coverage data exists (T-1676 makes that possible).
2. A no-progress watchdog: if the subprocess produces no output for N minutes, treat it as hung. This is the signal that actually distinguishes hung from slow.
3. Detect the specific xdist worker-death signature and rerun the unfinished work serially, which is the Makefile behavior that was never ported.
4. Never leave zombies: reap children and kill the process group on abort.

T-1672 covers the narrower 'a killed worker aborts the run' case; this is its more dangerous sibling -- the run that never ends at all. Fold T-1672 into this if one implementation covers both.