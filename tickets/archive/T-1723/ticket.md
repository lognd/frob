---
id: T-1723
title: 'post-land sweep regression from T-1677: 3 new error(s) (ARCH001, ARCH103,
  SEC110)'
state: dropped
kind: bug
origin: agent
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/testing/_coverage_refresh.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_coverage.py::TestSpawnWithWatchdog::test_wall_clock_deadline_kills_and_reports
- tests/test_coverage.py::TestSpawnWithWatchdog::test_no_progress_deadline_kills_a_silent_hang
- tests/test_coverage.py::TestSpawnWithWatchdog::test_killed_process_group_leaves_no_surviving_children
- tests/test_coverage.py::TestPytestOutcomeWorkerCrashRecovery::test_crash_signature_triggers_one_serial_retry
- tests/test_coverage.py::TestPytestOutcomeWorkerCrashRecovery::test_crash_signature_with_failing_retry_stays_degraded
- tests/test_coverage.py::TestPytestOutcomeWorkerCrashRecovery::test_ordinary_red_suite_is_not_classified_as_worker_crash
designated_repro_test: null
threat: null
component: null
---
The deferred post-land unscoped sweep (T-1684) for T-1677 at commit a209cd2e0974881d3392fca5d73d26e96eea8f36 found 3 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs:

- ARCH001  src/frob/testing/_coverage_refresh.py
- ARCH103  src/frob/testing/_coverage_refresh.py
- SEC110  src/frob/testing/_coverage_refresh.py

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-07: resolved by T-1672 (landed after this sweep ticket was filed): T-1672 already split _spawn_with_watchdog and extracted the worker-crash retry, and already carries a reasoned ARCH103 waiver on _kill_process_group. Verified against current merged main: frob check --only archgate --only secrets shows 0 errors for _coverage_refresh.py, and frob check --land-parity is clean, 0 unscoped errors repo-wide -- main is now at zero (absorbed by T-1672)