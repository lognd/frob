---
id: T-3174
title: T-2114 fork-based concurrent-writer sim spuriously skips lock contention once
  ledger_lock spans the fork point
state: done
kind: bug
origin: human
created: '2026-08-27'
priority: medium
blocked_by:
- T-3144
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'close-time and land-time BUG002/TEST016 both flag this test as confirmatory-only
    because the xfail marker at the parent commit hides the real failure from a normal
    pytest run; documented and manually verified the genuine repro via --runxfail
    in the Done report

    '
  actor: logan
  at: '2026-08-27'
  old_length: 3171
  new_length: 4042
evidence:
- tests/test_ticket_land.py::TestSquashSpliceLedgerChurn::test_concurrent_write_between_squash_and_splice_survives_land
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3163's production fix widens root's ledger_lock to span
compose_squash_in_disposable_worktree's entire lifetime (from before the
squash-merge through fold+CAS+resync), closing a real silent-ledger-data-
loss hole. That widening exposed a SEPARATE, pre-existing test-infra gap
in TestSquashSpliceLedgerChurn::test_concurrent_write_between_squash_and_
splice_survives_land's own T-2114 concurrent-writer simulation:

_t2114_concurrent_new_ticket is spawned via
multiprocessing.get_context("fork"). Once ledger_lock is held by the
PARENT process at the moment of fork (now true for most of this test's
own injected-hook window, since the lock starts before the squash-merge
that fires the hook), the forked CHILD process inherits:

1. a COPY of frob.tickets._store._lock_local's thread-local `held` dict,
   already containing the parent's (path -> (fd, depth)) entry for
   root's tickets.lock;
2. the SAME underlying open file description for that fd (fork()
   duplicates fds by reference, and POSIX flock state belongs to the
   open file description, not the process).

ledger_lock()'s reentrancy check (`held.get(key)`) then finds that
inherited entry in the child and takes the "already held, just bump
depth" branch WITHOUT ever calling os.open/fcntl.flock again -- so the
child never actually contends for the lock at all, even though it is a
genuinely separate OS process with no legitimate claim to it. The test's
own docstring for _t2114_concurrent_new_ticket already documents an
analogous fork-artifact problem for FROB_WORKTREE/FROB_AGENT (fixed by
T-3144, popping both in the child); this is the identical class of bug
for lock state instead of env vars.

MEASURED 2026-08-27 (T-3163): reproduced the SAME test scenario with a
standalone script using multiprocessing.get_context("spawn") instead of
"fork" (genuinely independent process, no inherited fd/thread-local
state) against T-3163's fixed production code -- PASS: the sibling
correctly blocks until land() fully resyncs, then reads the fresh
published ledger and appends cleanly; both tickets survive. Confirms the
production fix is correct and this is a test-construction artifact, not
a second production bug.

REPRO: with T-3163's ledger_lock widening applied, run
tests/test_ticket_land.py::TestSquashSpliceLedgerChurn::test_concurrent_write_between_squash_and_splice_survives_land
-- it still fails/xfails with the SAME symptom the widened lock was
meant to close (T-0001's own record missing from load_all), but this
time because the forked child skipped contention entirely, not because
of a real production race.

SUGGESTED FIX: switch this one test's multiprocessing context from
"fork" to "spawn" (mirroring the standalone repro), or explicitly reset
_lock_local's held dict (and close/reopen the inherited fd) at the top
of _t2114_concurrent_new_ticket before calling new_ticket, so the forked
child's book-keeping does not lie about lock ownership it was never
actually granted.

blocked_by T-3144: this file's write lease is currently held by T-3144
(same class of test-infra fix, different failing test); sequence after
that ticket lands to avoid a scope collision on the same file." 

frob:waive BUG002 reason="the designated evidence test (TestSquashSpliceLedgerChurn::test_concurrent_write_between_squash_and_splice_survives_land) genuinely reproduced the fork-vs-lock-inheritance artifact at the parent commit -- verified manually with pytest --runxfail, which showed a real, non-xfail-masked FAILURE there and a genuine PASS at this fix. BUG002/TEST016's automated pass/fail measurement uses a normal pytest run, where the parent commit's xfail(strict=True) marker reports the run as passing (an expected failure, not a failure) -- so the standard before/after comparison cannot see the delta this fix makes, even though it is real. This is a test-infra fix to the evidence test itself (the fix IS the test change), not new production code the test verifies from the outside, so there is no separate non-test caller to bind evidence against either."