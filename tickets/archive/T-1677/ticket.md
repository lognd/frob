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
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/testing/_coverage_refresh.py
- tests/test_coverage.py
- docs/modules/testing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
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
body_changes:
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _coverage_refresh.py'
  actor: logan
  at: '2026-09-19'
  old_length: 2374
  new_length: 4980
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
anchor: false
anchor_reason: null
land_commit: null
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

T-4718 sweep (condensed from src/frob/testing/_coverage_refresh.py:296-333,
trimmed for DOCARCH002's 12-line cap): the trimmed block's full original
text, kept verbatim below.

#: The xdist worker-crash signature this module knows how to detect and
#: retry serially (T-1672's "killed worker" incident, folded in here per
#: this ticket's own body: "fold T-1672 into this if one implementation
#: covers both"). `INTERNALERROR` is pytest's own marker for an
#: uncaught exception in its own machinery (xdist's scheduler raises
#: exactly this shape, `KeyError: <WorkerController gwNN>`, when a worker
#: process disappears out from under it, IF it happens); `gwNN` node-down
#: report lines are `execnet`'s. Matching any is enough to classify the
#: abort as an ENVIRONMENT failure (a worker got killed, most often OOM)
#: rather than a genuine test regression -- T-1672's item 3, "a resource
#: kill and a real suite failure both surface as exited 3; classify them
#: differently."
#:
#: T-2087: `worker\s+gw\d+\s+crashed` never actually matched on THIS
#: repo's pinned pytest-xdist (3.8.0) -- verified directly with both a
#: voluntary `os._exit` and a real `SIGKILL` inside a worker, run under
#: this repo's own installed xdist. The real summary line quotes the
#: node id (`worker 'gw1' crashed while running '...'`), which the old
#: pattern's bare `gw\d+` (no room for the surrounding `'...'`) could
#: never match. In practice this was masked rather than silent: every
#: reproduced crash shape ALSO printed `replacing crashed worker gwNN`
#: (the OTHER alternative here) earlier in the same output, so
#: `_pytest_outcome` still classified correctly end to end -- but the
#: summary-line branch existed to catch exactly the case where that
#: earlier line is NOT present in the captured output (e.g. a watchdog-
#: truncated capture, T-1677's own `_spawn_with_watchdog`), and in that
#: case it was silently dead. `'?` (both quote styles, and none, in one
#: pattern) fixes the summary-line branch without touching the other two.
#: The ORIGINAL `INTERNALERROR>...KeyError: <WorkerController gwNN>`
#: shape T-1672's own field incident recorded was NOT reproduced on this
#: pytest-xdist version despite both an `os._exit` and a `SIGKILL` repro
#: (see `TestWorkerCrashSignatureRealSubprocess` below) -- it may be
#: specific to an older xdist version this repo has since upgraded past;
#: the pattern is kept (matching it costs nothing and it may still occur
#: under a different failure timing this repro did not hit) but is no
#: longer the only, or even the primary, real-world match path.