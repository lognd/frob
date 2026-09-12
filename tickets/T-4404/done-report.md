## Done report

Root cause: on win32, orphaned_ticket_locks's liveness probe (_lock_file_held_by_live_process -> portable_flock_acquire -> _portable_flock_acquire_windows) seeds an empty lock file with a NUL byte + fsync before msvcrt.locking can lock a byte range (unlike fcntl.flock's whole-descriptor lock on POSIX). That seed-write bumps the file's mtime to now, so a lock file os.utime'd to a pre-cutover timestamp was stat'd AFTER the probe ran and read as post-cutover, defeating the T-4348 baseline exclusion. Fix: orphaned_ticket_locks now snapshots each lock file's mtime BEFORE calling the liveness probe, and _is_ticket_lock_baseline_excluded takes that snapshot as a caller-supplied lock_mtime instead of re-stat'ing lock_path itself; a no-op on POSIX. Measured: the failing node id passes on Linux and, via winrun from the worktree, passes on win32 (exit 0); the full TestOrphanedTicketLocks class (10 tests) also passes on win32. check-repro reports the node id as confirmatory-only (PASSED_AT_PARENT) -- expected: the bug is win32-only so on Linux the test already passed at parent. frob check --ticket T-4404: only PRE001 was ticket-specific (missing pre-work sweep), cleared via frob ticket sweep T-4404. Other FAIL rows are pre-existing repo-wide findings outside scope.

### Changed
```
 src/frob/tickets/_leases.py | 47 ++++++++++++++++++++++++++++++++++++++++-----
 tickets/T-4404/ticket.md    |  2 ++
 2 files changed, 44 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/test_ticket_leases.py::TestOrphanedTicketLocks::test_pre_cutover_lock_is_baseline_silent` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 7 error(s), 4824 warning(s), 961 waived
- error-findings: DOC006@tickets/T-4437/ticket.md, LARGE001@src/frob/strata/_native_staleness.py, MILE002@tickets.md, TICK004@tickets.md, TICK006@tickets.md, TICK010@/home/logan/projects/frob/.git/frob-leases/T-4412.json, TICK010@/home/logan/projects/frob/.git/frob-leases/T-4424.json
