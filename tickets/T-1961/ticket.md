---
id: T-1961
title: 'Ledger verbs refuse with LandInProgress instead of waiting: hit 4x in one
  hour, forces hand-rolled retry loops'
state: queued
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
designated_repro_test: null
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
