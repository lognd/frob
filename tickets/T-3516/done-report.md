## Done report

Implemented per the ticket body's 4-part ask, all in tests/conftest.py's
existing reporting plugin (SUITE-RESULT/SUITE-RESULT-FAILED/DID-NOT-
COMPLETE emitter):

1. pytest_runtest_logstart/pytest_runtest_logfinish write/clear a per-
   worker "currently running" marker under .frob/xdist-crash-marker/
   (worker id, nodeid, start time). pytest_handlecrashitem (xdist's own
   crashed-item hookspec, @pytest.hookimpl(optionalhook=True) so it never
   errors when xdist is disabled, e.g. this repo's own -p no:xdist
   dispatch convention) reads that marker to infer timeout-vs-OOM
   (elapsed >= the run's configured --timeout means "exceeded Ns timeout
   (thread-method os._exit)", well short of it means "suspect OOM").

2. The crashed test's report.outcome stays xdist's own default "failed"
   unconditionally (never a silent skip) -- it already lands in
   SUITE-RESULT-FAILED via terminalreporter.stats without any change
   needed there; pytest_sessionfinish now appends the inferred
   cause+disposition to that one line for a crashed nodeid only,
   byte-for-byte unchanged for an ordinary failure.

3. pytest_sessionfinish prints ONE WORKER-CRASH-REPORT: N header plus one
   line per crash (same write_line channel as SUITE-RESULT), and forces
   session.exitstatus to 1 if a crash occurred but the computed status
   would otherwise read clean (a capped rerun that happened to pass must
   not hide the crash). _harden_dsession_active_nodes monkeypatches
   xdist.dsession.DSession.worker_workerfinished/worker_errordown so a
   SECOND crash-adjacent callback for an already-removed WorkerController
   calls set.discard instead of set.remove -- this is the actual root
   cause of the observed INTERNALERROR> KeyError: <WorkerController gwN>
   (both methods tail-call self._active_nodes.remove(node); a real race
   in xdist's own bookkeeping when both callbacks fire for the same dying
   worker).

   _WORKER_CRASH_RERUN_CAP defaults to 0 (no automatic reschedule): xdist
   does not retry a crashed test on its own, only a pytest_handlecrashitem
   implementation that calls sched.mark_test_pending does, and a
   deterministic crasher rescheduled once would just crash its fresh
   worker too, turning MUST-FIRE's "exactly one entry" into a cascade.
   The reschedule mechanism itself is real and unit-tested (monkeypatched
   cap) for a future ticket to raise once there is a reliable way to
   distinguish "transient" from "deterministic".

4. .github/workflows/ci.yml's ubuntu Test step now tees its own output to
   a log file (pipefail preserves the real exit code), and a new
   always()-run step greps that log for WORKER-CRASH-REPORT: lines into
   GITHUB_STEP_SUMMARY -- visible without scrolling the raw log, on both
   a passing and a failing/timed-out Test step.

design/frob.strata: declared the fs.write/fs.read/exec/env.read
capabilities T-3516's new code introduces on the testsuite node
(SELFAUDIT001) -- the marker file I/O, and
TestWorkerCrashReportIntegration's real `python -m pytest -n 2` subprocess
runs (the only way to exercise an actual xdist worker crash end-to-end;
the unit-level fakes in TestWorkerCrashReport cover the hook logic itself
in isolation).

MUST-FIRE (tests/unit/test_conftest_stackdump.py::
TestWorkerCrashReportIntegration::
test_must_fire_planted_os_exit_produces_one_report_and_failing_exit):
a planted `os._exit(1)` test under a real subprocess `pytest -n 2` run
produces exactly one WORKER-CRASH-REPORT entry naming it, exactly one
SUITE-RESULT-FAILED entry naming it, a nonzero process exit code, and no
INTERNALERROR anywhere in the output. PASSING.

MUST-STAY-QUIET (same class, test_must_stay_quiet_on_a_clean_run and
test_must_stay_quiet_normal_failure_reporting_unchanged): a clean run
prints no WORKER-CRASH-REPORT section at all; an ordinary (non-crashing)
failing test's SUITE-RESULT-FAILED line is byte-for-byte unchanged (no
crash-cause suffix, no report section). Both PASSING.


Note: `uv run frob test --base main` fell back to a suite-wide selection
(fallback=package for tickets/T-3516/ticket.md, an unknown-language
touched path) and exceeded the 540s budget without completing -- relying
on the scoped `pytest -p no:xdist tests/unit/test_conftest_stackdump.py
tests/unit/test_conftest_suite_result_status.py` run instead (23
collected, 0 failed, includes all 12 new T-3516 tests: 6 unit-level
hook/report tests plus 3 real-subprocess MUST-FIRE/MUST-STAY-QUIET
integration tests, plus 3 pre-existing sibling suite-result tests
confirming no regression).

Also fixed while landing: a killed `frob check --fix` (unscoped Tier-A
pass, twice) left uncommitted stray edits across ~14 unrelated files
outside this ticket's scope (deleted `_build_parser` from
src/frob/_cli_parsers/_root.py among them, breaking the whole `frob` CLI)
-- reverted every one of those files with `git checkout --` before
proceeding; none of that stray damage is part of this ticket's diff.

### Changed
```
 .github/workflows/ci.yml              |  26 ++-
 design/frob.strata                    |  20 +-
 tests/conftest.py                     | 378 ++++++++++++++++++++++++++++++++--
 tests/unit/test_conftest_stackdump.py | 360 +++++++++++++++++++++++++++++++-
 tickets/T-3516/ticket.md              |  23 ++-
 5 files changed, 776 insertions(+), 31 deletions(-)
```

### Evidence
- `tests/unit/test_conftest_stackdump.py::TestWorkerCrashReport::test_logstart_writes_marker_only_on_worker` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_stackdump.py::TestWorkerCrashReport::test_logfinish_clears_marker` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_stackdump.py::TestWorkerCrashReport::test_handlecrashitem_records_one_entry_and_marks_failed` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_stackdump.py::TestWorkerCrashReport::test_handlecrashitem_respects_a_raised_rerun_cap` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_stackdump.py::TestWorkerCrashReport::test_sessionfinish_prints_report_and_forces_failing_exit` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_stackdump.py::TestWorkerCrashReport::test_sessionfinish_stays_quiet_on_a_clean_run` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_stackdump.py::TestWorkerCrashReportIntegration::test_must_fire_planted_os_exit_produces_one_report_and_failing_exit` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_stackdump.py::TestWorkerCrashReportIntegration::test_must_stay_quiet_on_a_clean_run` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_stackdump.py::TestWorkerCrashReportIntegration::test_must_stay_quiet_normal_failure_reporting_unchanged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 19 error(s), 4122 warning(s), 875 waived
- error-findings: ARCH103@src/frob/tickets/_leases.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/macos-portability.md, DOC007@src/frob/verify/_bisect.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT002@src/frob/verify/_bisect.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3516, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, SELFAUDIT001@docs/design/registry/capability-via-ratchet.lock.json, TICK004@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json
