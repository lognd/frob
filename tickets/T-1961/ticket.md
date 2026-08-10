---
id: T-1961
title: 'Ledger verbs refuse with LandInProgress instead of waiting: hit 4x in one
  hour, forces hand-rolled retry loops'
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_leases.py
- tests/test_ticket_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/
  reason: 'TICK009 breadth: the umbrella src/frob/tickets/ collided with T-1948''s
    live lease and suppressed this high-priority unblocked ticket from the doable
    queue entirely. LandInProgress is raised only in src/frob/tickets/_leases.py (and
    consumed in _rapid_sweep.py); narrowing to the actual refusal site plus its test
    file. Measured: git grep -ln LandInProgress -- src/ returns exactly two files.'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/tickets/_leases.py
  reason: 'TICK009 breadth: the umbrella src/frob/tickets/ collided with T-1948''s
    live lease and suppressed this high-priority unblocked ticket from the doable
    queue entirely. LandInProgress is raised only in src/frob/tickets/_leases.py (and
    consumed in _rapid_sweep.py); narrowing to the actual refusal site plus its test
    file. Measured: git grep -ln LandInProgress -- src/ returns exactly two files.'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/test_ticket_leases.py
  reason: 'TICK009 breadth: the umbrella src/frob/tickets/ collided with T-1948''s
    live lease and suppressed this high-priority unblocked ticket from the doable
    queue entirely. LandInProgress is raised only in src/frob/tickets/_leases.py (and
    consumed in _rapid_sweep.py); narrowing to the actual refusal site plus its test
    file. Measured: git grep -ln LandInProgress -- src/ returns exactly two files.'
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_waits_then_succeeds_once_the_lock_frees
- tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_wait_times_out_and_still_refuses_loudly
designated_repro_test: tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_waits_then_succeeds_once_the_lock_frees
threat: null
component: null
anchor: false
anchor_reason: null
---
REPEATED-MISTAKE AUDIT (2026-08-10). Every ledger-writing verb refuses
outright while any land holds the repo lock:

  ERROR: ticket new: refused -- LandInProgress: a land is in progress
  for this repository; retry after it completes

MEASURED THIS SESSION: this refusal hit the coordinator FOUR times in one
hour, on `frob ticket new` (x3, filing T-1950, T-1955, T-1960) and
`frob ticket block` (x1, blocking T-1951 on T-1941). Each time the work
was pure ledger bookkeeping with no interaction whatsoever with the
in-flight land's content. The workaround was a hand-written 60-iteration
retry loop with `sleep 10` -- written twice, because it is not part of any
tool.

WHY IT COSTS THROUGHPUT: with 5 agents landing in parallel (the standing
dispatch target), the land lock is held a large fraction of the time. The
coordinator's job during a wave is almost entirely filing tickets from
agent reports, so the two collide constantly. Worse, the refusal is
INDISTINGUISHABLE at a glance from a real failure -- it exits non-zero,
so an unattended script reads it as "ticket not filed" and a finding is
silently lost. That is the actual risk here, beyond the wasted minutes.

DO NOT FIX IT THIS WAY:
- Do NOT simply drop the lock check. It exists because concurrent ledger
  writes during a land corrupt the ticket ledger, and this repo has
  already taken every gate down once with a bad ledger write.
- Do NOT make callers responsible for retrying. That is a command
  requiring knowledge of the command, and it has already been
  hand-rolled twice; the third writer will get the backoff wrong.

FIX DIRECTION, preferred order:
(a) Have the ledger-writing verbs WAIT on the lock (bounded, with a
    visible "waiting for in-flight land..." message and a timeout) rather
    than refuse. The caller's intent is unambiguous -- it wants the
    ticket filed -- and blocking briefly is strictly better than
    exiting 1.
(b) If some verbs genuinely cannot wait, distinguish the exit code for
    "refused because busy, retry is safe" from "refused because wrong",
    so automation can tell a transient from a real failure.

Note `frob ticket new` already auto-commits its own ledger write, so the
serialization point is understood; this is about queueing on it rather
than bouncing off it.

ACCEPTANCE: first test must FAIL before the fix -- hold the land lock,
invoke `frob ticket new`, and assert it succeeds after the lock releases
rather than exiting non-zero. Then assert a lock held past the timeout
still fails loudly (no unbounded hang), and that the ledger is not
corrupted by a write that waited.

## Done report

Changed:
src/frob/tickets/_leases.py::refuse_if_land_in_progress (now waits, bounded)
src/frob/tickets/_leases.py::_probe_land_once (new, extracted for ARCH001)
src/frob/tickets/_leases.py::_land_flock_probe (added quiet= param)
src/frob/tickets/_leases.py::_refuse_for_held_land_lock (added quiet= param)

Evidence:
tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_waits_then_succeeds_once_the_lock_frees
tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_wait_times_out_and_still_refuses_loudly
Repro confirmed both via frob's own --check-repro-force (same known
PYTHONPATH bug as T-2005) and directly via git show on the parent
commit's source (old signature has no wait_timeout_s kwarg).

Filed: none new (T-2005 already covers the check-repro PYTHONPATH bug)

Gates: full tests/test_ticket_leases.py suite green except one
pre-existing, unrelated failure (TestLedgerAutoCommitEnumeratedOverDispatchTable::test_dispatch_table_verbs_are_all_accounted_for,
already broken at main tip 392fb9cd5 before this ticket -- a prior
land added an "anchor" verb to the dispatch table without updating
this enumeration test; confirmed via git grep on main, not introduced
here). ARCH001/ty clean on src/frob/tickets/_leases.py.

Direction (a) implemented per the ticket's own preferred order: the
lock check itself and T-1619's belt-and-braces process scan are
unchanged; callers are not made responsible for retrying.

### Changed
```
 src/frob/tickets/_leases.py | 177 ++++++++++++++++++++++++++++----------------
 tests/test_ticket_leases.py | 115 +++++++++++++++++++++++++++-
 tickets/T-1961/ticket.md    |   7 +-
 3 files changed, 228 insertions(+), 71 deletions(-)
```

### Evidence
- `tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_waits_then_succeeds_once_the_lock_frees` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_wait_times_out_and_still_refuses_loudly` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/gates/_fix_engine_sync.py, COV003@tickets/T-0907, F401@/home/logan/projects/frob/.claude/worktrees/t1961-series/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/t1961-series/tests/unit/test_tickets_evidence_only_scope.py, PRE001@tickets/T-1961
