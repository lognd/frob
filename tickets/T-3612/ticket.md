---
id: T-3612
title: narrow LandInProgress to the ledger-splice critical section for tickets-dir
  writers
state: queued
kind: ux
origin: human
created: '2026-08-31'
priority: high
parent: T-3611
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: consumer corroboration F-099 plus four first-hand refusals today; records
    how this compounds with T-3885s predicate over-match and why T-3892s mirror fix
    must land first
  actor: logan
  at: '2026-09-05'
  old_length: 1004
  new_length: 3401
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Filing verbs (new/drop/body/scope/fail) write only the tickets dir yet
are refused with LandInProgress for a land's ENTIRE multi-minute
duration (flock probe + T-1619 process scan, _leases.py:2017+). The
actual race they guard is the land's ledger SPLICE -- a short critical
section that already runs under tickets.lock.

Fix: scope the refusal to the splice critical section. Ticket-file
writers take tickets.lock (they already do); the land holds tickets.lock
only during its splice; outside that window, filing/dropping during a
land is safe -- the land's splice re-reads the ledger under the lock.
Delete or narrow the whole-land flock probe + process-scan refusal for
these verbs (keep it for a second land). Add a two-process test: a land
in its slow phase (gates) while a file verb succeeds; a land in its
splice while the file verb blocks briefly then succeeds; never a
corrupted ledger. Measure before/after: time-to-file during a busy
fleet drops from unbounded (window starvation) to <2s p95.



CONSUMER CORROBORATION AND FIRST-HAND MEASUREMENT, 2026-09-05.

logand.app-v2 F-099: "`frob ticket scope --add` from a worktree refuses to
mirror to main while any land is in progress". That is this ticket's premise,
reported independently by a consumer repo.

I HIT THE SAME REFUSAL FOUR TIMES IN A ROW as coordinator today, on
`frob ticket new`, over roughly fifteen minutes -- including on the attempt to
file the ticket describing the defect that was causing it. Each refusal was
correct given the current predicate; the predicate is the problem.

TWO THINGS THAT MAKE THIS WORSE THAN A WAIT, and both argue for narrowing rather
than for a longer timeout:

  1. IT COMPOUNDS WITH T-3885. That ticket records two over-matches in T-1619's
     belt-and-braces process scan: it does not filter by TARGET REPOSITORY (a
     land in ../logand.app-v2 blocked writes here -- measured, pid 1095675,
     cwd /home/logan/projects/logand.app-v2), and it does not exclude the
     land's OWN CHILD pids (F-098, a self-deadlock). So "any land in progress"
     can mean a land in a different repo, or a phantom land that is really this
     land's own descendant. Narrowing the WINDOW (this ticket) and narrowing
     the PREDICATE (T-3885) are complementary; neither alone is sufficient.

  2. THE MIRROR IT IS PROTECTING IS ITSELF DEFECTIVE. T-3892 records that the
     scope mirror writes a ticket to main WITHOUT its evidence block, so a
     later `git merge main` conflicts on `evidence:` and has twice left
     conflict markers inside YAML frontmatter -- crashing every `frob ticket`
     command in that worktree. So the current behaviour blocks a write in
     order to protect a splice that corrupts the ledger when it does run.
     Sequence the two: T-3892's mirror fix should land BEFORE this ticket
     widens how often the mirror runs, or the outcome is more corruption, more
     often.

WHY THE PROTECTION MUST SURVIVE ANYWAY: T-1619 exists because the land lock
alone was insufficient -- a land can be mid-ledger-splice while its flock is not
currently held, and a concurrent ledger write in that window corrupts the
splice. Narrowing to the actual critical section is right; removing the guard is
not.

FIXTURE TO ADD: a ledger write attempted DURING the real splice window is still
refused; a ledger write attempted while a land is merely running, outside that
window, succeeds.
