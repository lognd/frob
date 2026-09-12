---
id: T-4404
title: 'orphaned_ticket_locks reports pre-cutover lock on Windows: baseline exclusion
  not silent'
state: in-progress
kind: bug
origin: human
created: '2026-09-10'
priority: medium
parent: T-3505
tier: ticket
sprint: v0.531.0
runs_last: false
milestone: v0.531.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_leases.py
- tests/test_ticket_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: parent
  old_value: null
  new_value: T-3505
  reason: windows drain epic T-3505 covers this leaf
  actor: logan
  at: '2026-09-11'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 34546329688, Windows leg only.

Node id: tests/test_ticket_leases.py::TestOrphanedTicketLocks::test_pre_cutover_lock_is_baseline_silent

Assertion (verbatim):
    assert orphaned_ticket_locks(repo) == ()
E   AssertionError: assert ('T-3333',) == ()
E   Full diff:
E   - ()
E   + (
E   +     'T-3333',
E   + )

The test creates T-3333.lock, sets its mtime before _ORPHAN_LOCK_BASELINE_
CUTOVER via os.utime, and expects _is_ticket_lock_baseline_excluded to
silence it (T-4348 baseline). On Windows it is reported instead, meaning
either the lock_path.stat().st_mtime comparison against the cutover
constant does not agree with the os.utime-set value on this platform
(NTFS timestamp precision/epoch rounding), or _lock_file_held_by_live_
process (portable_flock_acquire, _open_land_lock_fd_for_probe) is not
correctly probing the empty just-touched file as not-held on win32,
so the function never reaches the baseline check with the value the test
expects, or takes a path that alters the mtime. Investigate on the
Windows mirror (see windows-is-verifiable-locally memory) to find which of
the two probes disagrees on win32, then make production code
platform-correct with a declared sys.platform reason rather than
adjusting the test's expectation.