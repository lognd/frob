---
id: T-3516
title: Collect xdist worker crashes into one loud end-of-run WORKER-CRASH-REPORT instead
  of mid-stream node-down spam and INTERNALERROR aborts
state: done
kind: bug
origin: human
created: '2026-08-30'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/conftest.py
- tests/unit/test_conftest_stackdump.py
- .github/workflows/ci.yml
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: design/frob.strata
  reason: SELFAUDIT001 requires declaring the fs.write/fs.read/exec/env.read capabilities
    T-3516's new crash-marker + subprocess-integration-test code introduces on the
    testsuite node
  actor: logan
  at: '2026-08-30'
evidence:
- tests/unit/test_conftest_stackdump.py::TestWorkerCrashReport::test_logstart_writes_marker_only_on_worker
- tests/unit/test_conftest_stackdump.py::TestWorkerCrashReport::test_logfinish_clears_marker
- tests/unit/test_conftest_stackdump.py::TestWorkerCrashReport::test_handlecrashitem_records_one_entry_and_marks_failed
- tests/unit/test_conftest_stackdump.py::TestWorkerCrashReport::test_handlecrashitem_respects_a_raised_rerun_cap
- tests/unit/test_conftest_stackdump.py::TestWorkerCrashReport::test_sessionfinish_prints_report_and_forces_failing_exit
- tests/unit/test_conftest_stackdump.py::TestWorkerCrashReport::test_sessionfinish_stays_quiet_on_a_clean_run
- tests/unit/test_conftest_stackdump.py::TestWorkerCrashReportIntegration::test_must_fire_planted_os_exit_produces_one_report_and_failing_exit
- tests/unit/test_conftest_stackdump.py::TestWorkerCrashReportIntegration::test_must_stay_quiet_on_a_clean_run
- tests/unit/test_conftest_stackdump.py::TestWorkerCrashReportIntegration::test_must_stay_quiet_normal_failure_reporting_unchanged
designated_repro_test: tests/unit/test_conftest_stackdump.py::TestWorkerCrashReportIntegration::test_must_fire_planted_os_exit_produces_one_report_and_failing_exit
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 300f4f9448638006161aabe1f71670d430eb1dc4
---
OWNER REQUEST (2026-08-30): ubuntu CI runs intermittently emit raw xdist
worker-crash noise mid-stream -- "[gwN] node down: Not properly terminated",
"replacing crashed worker", INTERNALERROR KeyError: <WorkerController gwN> --
observed in runs 33284942175, 33289332473, 33303586303, 33336905168 and in
local full-suite runs. The dominant cause is known and being reduced (the
frob_self_scan_heavy tests exceeding their 300s pytest-timeout, whose
thread-method watchdog os._exit()s the worker; T-3495 cut that group 4.3x),
but the REPORTING is the defect this ticket owns: a worker death today
scatters unstructured spam through the progress stream, can abort the whole
session (exitstatus=3 INTERNALERROR, run 33291796476-adjacent local repro),
and leaves the operator to reconstruct which test died and why from
faulthandler fragments.

WANTED: collect, do not scatter -- and stay loud.
 1. In tests/conftest.py (this repo already owns a reporting plugin there --
    the SUITE-RESULT / SUITE-RESULT-FAILED emitter and the DID-NOT-COMPLETE
    line): implement pytest-xdist's crashed-item hook
    (pytest_handlecrashitem) to RECORD each crash: worker id, test nodeid,
    and inferred cause -- correlate with the pytest-timeout/faulthandler
    dump if one was emitted for that worker (timeout kill) versus none
    (OOM-kill/hard death), plus rerun disposition.
 2. Mark the crashed test as a FAILED item with a one-line message
    ("worker gw3 died running <nodeid>: exceeded 300s timeout (thread-method
    os._exit)" or "worker died without a dump -- suspect OOM") so it appears
    in SUITE-RESULT-FAILED like any other failure -- never a silent skip. If
    xdist would reschedule the test on a fresh worker, cap that at one rerun
    and record the disposition in the report.
 3. Print ONE end-of-run "WORKER-CRASH-REPORT:" section (same channel as
    SUITE-RESULT) listing every crash with the fields above; keep the run's
    exit status failing whenever a crash occurred. The mid-stream xdist
    lines cannot be fully suppressed from xdist itself, but the session must
    no longer ABORT on a crash (the KeyError/INTERNALERROR path in the
    DID-NOT-COMPLETE collector must handle a vanished WorkerController and
    keep collecting), and the collected section is the authoritative,
    greppable record.
 4. CI (.github/workflows/ci.yml) greps: extend the SUITE-RESULT extraction
    comments/step (if any) to surface WORKER-CRASH-REPORT in the step
    summary so the report is visible without scrolling the raw log.
MUST-FIRE: a planted test that os._exit()s its worker produces exactly one
WORKER-CRASH-REPORT entry naming it, a FAILED entry in SUITE-RESULT-FAILED,
and a failing exit status -- with no INTERNALERROR abort.
MUST-STAY-QUIET: a clean run prints no WORKER-CRASH-REPORT section, and a
normally-failing (non-crashing) test's reporting is unchanged.