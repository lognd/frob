## Done report

Self-healing land.lock (T-1634).

Root cause: the actual `_land_lock` acquisition was never really blocked
by a dead holder -- the OS releases `flock` the instant a process exits,
SIGKILL included. The real bug was `frob doctor`'s health computation:
`scan_live_land_processes` read the stale JSON content left behind and
marked `DoctorReport.healthy = False` for a CONFIRMED-dead holder, and
`make coverage`/`make coverage-fast`'s own recipe gates its pytest/`frob
coverage` invocation on `frob doctor`'s exit code -- so a leftover file
from a killed land failed an unrelated Makefile target for hours until a
human noticed and deleted `.frob/land.lock` by hand.

Fix, in two parts:
1. `frob.tickets._land._probe_land_lock_pid_liveness(pid) -> bool | None`:
   a new shared three-state pid-liveness probe (True/False/None), mirroring
   the confirmed_absent/ambiguous split `frob.tickets._leases.
   _probe_worktree_liveness` already draws for worktree leases. Used by
   both `_land_lock` and `frob.doctor.scan_live_land_processes` -- one
   liveness notion for land.lock, not two.
2. `_land_lock` now reads the PRIOR holder's content right after acquiring
   the flock (whether immediate or after waiting) and, if that holder's pid
   is CONFIRMED dead, logs a loud WARNING disclosing the dead holder's
   identity before overwriting the file with this process's own metadata --
   the disclosure T-1634 asked for. (This does not, and must not, unlink
   the file mid-acquire: the same fd is about to overwrite its content, and
   unlinking-by-path would sever the path from the inode the fd writes
   into. Verified against the existing test that holds a REAL flock on a
   file naming a fake-dead pid -- that test still correctly times out,
   proving the fix never overrides a genuinely-held OS lock based on
   metadata alone.)
3. `frob doctor`: `DoctorReport.healthy` no longer goes False for a
   CONFIRMED-dead holder (`alive is False`) -- only for an AMBIGUOUS probe
   (`alive is None`, e.g. a PermissionError) does it still block, matching
   the leases module's own confirmed_absent/ambiguous distinction. The
   finding is still disclosed: `_combined_remediation` still names the
   dead holder (now describing it as self-healing, not requiring a human
   fix), and `doctor_runner.py`'s plain-text CLI output prints an explicit
   info line on the otherwise-healthy path so the finding is never dropped
   from the human-readable report, honoring this file's existing "doctor
   only ever reports, it never repairs" design (see
   `scan_stale_ticket_leases`'s docstring) -- doctor does not mutate
   `.frob/land.lock` itself; the next real `_land_lock` acquisition is
   what performs the actual reclaim.

Other rules with the same pre-work/in-progress confusion: none found in
this ticket's own scope. `frob doctor`'s stale-ticket-lease scan already
gets this right (reports, points at `frob ticket requeue`, never mutates).
This ticket's confusion was different in shape from T-1639/T-1645's (a
diagnostic treating "the holder is definitely gone" the same as "we
cannot tell" instead of treating "before work" the same as "during work"),
so I would not fold it into the same fix pattern those two tickets share.

Tests added/renamed:
- tests/test_ticket_land.py::TestLandLockHolderMetadataAndTimeout.test_orphaned_lock_from_a_confirmed_dead_pid_is_reclaimed_and_logged (new)
- tests/test_ticket_land.py::TestLandLockHolderMetadataAndTimeout.test_orphaned_lock_naming_a_genuinely_live_pid_still_refuses (new; renamed from the pre-existing fake-pid+real-flock test, unchanged behavior, new name/docstring only)
- tests/system/test_cli_doctor.py::TestDoctorLiveLandProcess.test_dead_holder_pid_is_reported_dead_but_self_healing_and_healthy (renamed+rewritten from test_dead_holder_pid_is_reported_dead_and_unhealthy; T-1515's evidence rebound via `frob ticket evidence T-1515 --archived --replace`)
- tests/system/test_cli_doctor.py::TestDoctorLiveLandProcess.test_ambiguous_holder_liveness_is_reported_unhealthy (new)

Verification:
- `uv run pytest tests/test_ticket_land.py -k LandLock` -- 5 passed
- `uv run pytest tests/system/test_cli_doctor.py` -- 37 passed
- `uv run pytest tests/system/test_cli_doctor.py tests/unit/test_makefile_coverage.py` -- 62 passed
- `uv run frob check --only gates-fast --ticket T-1634` -- 0 errors (5441 repo-wide warnings, all pre-existing per gate:scope-note)
- `uv run frob check --land-parity` -- clean, 0 unscoped errors

Not done / follow-ups: the ticket also asked "whatever cleanup path
exists must run on the abort paths a land already has" -- verified this
is already satisfied without new code: the stale-content-reclaim
disclosure lives in `_land_lock`'s acquire path itself (runs on every
`land()` call regardless of how the PREVIOUS one exited), and `frob
doctor` is a standalone diagnostic invoked independently of any land
abort path, so no additional wiring into `_land_locked`'s own unwind
logic was needed.

### Changed
```
 tickets.md | 46 ++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 44 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestLandLockHolderMetadataAndTimeout::test_orphaned_lock_from_a_confirmed_dead_pid_is_reclaimed_and_logged` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandLockHolderMetadataAndTimeout::test_orphaned_lock_naming_a_genuinely_live_pid_still_refuses` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorLiveLandProcess::test_dead_holder_pid_is_reported_dead_but_self_healing_and_healthy` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorLiveLandProcess::test_ambiguous_holder_liveness_is_reported_unhealthy` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorLiveLandProcess::test_live_holder_pid_is_reported_alive_and_healthy` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 0 error(s), 5531 warning(s), 849 waived
- error-findings: none (measured, zero errors)
