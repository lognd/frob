## Done report

The 2026-08-04 incident (T-1495): an orphaned background land driver
from a dead conversation was serially landing a roster while a NEW
coordinator session also wrote to main; the advisory flock-based
land.lock correctly serialized the two writers against each other but
gave neither session any way to tell the other holder was a foreign,
possibly-defunct driver rather than its own prior in-flight call -- a
blocking flock just queues silently forever.

Implemented, all three requested pieces:
1. land.lock records pid+session+start-time: _land_lock_holder_metadata
   builds {pid, session_id, started_at} (session_id defaults to
   pid-<pid>, or FROB_LAND_SESSION_ID if a caller/test sets it) and
   _land_lock writes it (JSON) into land.lock's own content on every
   successful acquisition.
2. A fresh land invocation logs who holds it and refuses after timeout:
   _land_lock no longer does an unconditional blocking flock -- it polls
   a non-blocking attempt every 1s, logs (once, at WARNING) the current
   holder's metadata the first time it has to wait at all, and raises
   LandLockTimeout after _LAND_LOCK_TIMEOUT_S (600s default, overridable
   via the timeout= kwarg) if the lock is still held. land()/land_plan()
   both catch LandLockTimeout and return
   Err(LandError.LandLockTimeout) (a new LandError variant) instead of
   blocking forever.
3. frob doctor reports live land processes: scan_live_land_processes
   reads root's .frob/land.lock content and reports a LiveLandProcess
   (pid, session_id, started_at, alive) with a POSIX liveness probe
   (os.kill(pid, 0)) against the recorded pid. Wired into
   DoctorReport.live_land_process, _collect_doctor_scans,
   _log_doctor_diagnosis, _assemble_doctor_report, and
   _combined_remediation. A LIVE holder is informational only (does not
   affect healthy/remediation -- an in-flight land() is normal); a DEAD
   (orphaned) holder DOES make healthy False, with a remediation naming
   the exact stale-lock repair.

Deliberately no hostname lookup in the holder metadata (a bare pid is
sufficient to disambiguate processes on the one host this lock file's
checkout lives on) -- this also keeps the tickets_ledger node's SYS100
capability surface at plain env (the FROB_LAND_SESSION_ID read), not net.

New docs section: docs/guides/install.md#live-land-process-report-t-1515,
frob:doc-anchored from LiveLandProcess, scan_live_land_processes, and
LandLockTimeout.

Tests added:
- tests/test_ticket_land.py::TestLandLockHolderMetadataAndTimeout --
  holder metadata is written and parses on acquire; the lock is released
  (fresh non-blocking acquisition succeeds) after the context exits; a
  foreign holder that never releases causes LandLockTimeout with the
  holder metadata attached, within a short test timeout (0.2s).
- tests/system/test_cli_doctor.py::TestDoctorLiveLandProcess -- no lock
  file reports nothing; this test process's own (genuinely live) pid is
  reported alive and does not affect healthy; a synthetic dead pid is
  reported alive=False and makes run_diagnosis unhealthy with a
  remediation naming the pid; malformed/empty lock content reports
  nothing (never raises).

Not closed via the standalone `frob ticket close` CLI in this worktree:
this ticket's diff adds new public API (LiveLandProcess,
scan_live_land_processes, LandLockTimeout, DoctorReport.
live_land_process) which trips close's own REL001 pre-close obligation
check (_own_obligations_rel_bump_dirty) -- that check requires a version
bump, which per T-0731 is land-owned and never performed in a worktree.
land()'s own internal close path (_land_finalize_and_close) does not run
this CLI-only pre-close obligation check, so `frob ticket land` closes
this cleanly; only the standalone `frob ticket close` CLI is blocked.
Same disposition as T-1514 in this same worktree/session.

### Changed
```
 design/frob.strata                        |  12 +-
 docs/guides/install.md                    |  49 ++++++
 frob.lock                                 |   2 +-
 src/frob/app/ticket_runner/_land_cmd.py   | 249 ++++++++++++++++++++++++++----
 src/frob/doctor.py                        | 113 +++++++++++++-
 src/frob/tickets/_land.py                 | 217 ++++++++++++++++++++++----
 src/frob/tickets/_land_squash.py          |  57 ++++++-
 src/frob/tickets/_models.py               |  16 ++
 tests/system/test_cli_doctor.py           | 108 +++++++++++++
 tests/test_ticket_land.py                 | 173 +++++++++++++++++++++
 tests/test_ticket_work_and_land_finish.py | 159 ++++++++++++++++++-
 tickets.md                                | 150 +++++++++++++++++-
 12 files changed, 1232 insertions(+), 73 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestLandLockHolderMetadataAndTimeout::test_holder_metadata_written_on_acquire` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandLockHolderMetadataAndTimeout::test_lock_released_after_context_exits` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandLockHolderMetadataAndTimeout::test_timeout_raises_when_a_foreign_holder_never_releases` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorLiveLandProcess::test_no_lock_file_reports_nothing` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorLiveLandProcess::test_live_holder_pid_is_reported_alive_and_healthy` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorLiveLandProcess::test_dead_holder_pid_is_reported_dead_and_unhealthy` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorLiveLandProcess::test_malformed_lock_content_reports_nothing` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 5 error(s), 135 warning(s), 781 waived
- error-findings: AFFECT001@src/frob/tickets/_land.py, AFFECT001@src/frob/tickets/_models.py, DOC002@src/frob/app/ticket_runner/_land_cmd.py, E501@/home/logan/projects/frob/.claude/worktrees/t-1513/src/frob/doctor.py:348, SEC110@src/frob/tickets/_land.py
