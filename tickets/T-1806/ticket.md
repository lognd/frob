---
id: T-1806
title: 'Generalize lease staleness: path-gone, ticket-gone, and holder-dead are all
  the same check'
state: queued
kind: bug
origin: human
created: '2026-08-07'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_leases.py
- src/frob/app/worktree_runner.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
A third orphaned-lease shape, found live while clearing
`.git/frob-leases/T-draft-30ce107e.json` (a retired agent's worktree):
the ticket id it named did not exist in main's ledger at all (a DRAFT
that lived only in that worktree's own local ledger, never promoted),
its worktree PATH still existed on disk, but no live process owned it.

All three supported recovery paths refused, each correctly by its own
narrow rule, producing a genuine deadlock:
- `frob worktree remove <path>` -> `kept:lease(T-draft-30ce107e 7643s)`
  (correct: never remove a worktree still holding a lease)
- `frob worktree release-lease` -> not applicable (T-1789's detector only
  covers a lease whose recorded WORKTREE PATH no longer exists; this
  path still existed)
- `frob ticket drop T-draft-30ce107e` -> `NotFound` (the draft never
  existed in main's ledger to drop -- it lived only in the dead
  worktree's own local view)

Recovered by hand: `rm .git/frob-leases/T-draft-30ce107e.json`, the
exact "no scoped verb exists, so raw filesystem work it is" pattern that
ran through all seven T-1779 incidents.

GENERALIZATION (the actual ask, not a fourth special case): a lease is
STALE if ANY of three independent conditions holds, not just the one
T-1789 currently checks:

1. Path gone (T-1789's `orphaned_leases`/`release_orphaned_lease`,
   already shipped).
2. Ticket gone -- the lease names an id absent from main's authoritative
   ledger. Trivially checkable (load_queue + membership test), currently
   UNCHECKED, and it is what hard-deadlocked this exact incident: the
   verb that would release it (`ticket drop`) cannot find the ticket to
   drop in the first place.
3. Holder dead -- path and ticket both exist, but no live process
   occupies the worktree (T-1739's own liveness probe,
   `scan_for_live_worktree_process`, already exists and is exactly the
   right check -- it is just never run against a HELD lease today, only
   against a worktree during `sweep`/`remove`).

Prefer ONE check ("is this lease still valid, for any reason") over
three special cases bolted together -- this is the third time in one
session lease-lifetime and ticket-lifetime have come apart differently;
a fourth shape is likely, and each new one should not need its own new
verb.

TWO DESIGN POINTS from the incident, not prescriptions:

- `frob worktree remove` should be able to SAY WHY it refused and name
  the specific release path, not just print `kept:lease(...)` with no
  next step. It already knows the ticket id at that moment -- it can
  check whether that id exists in the ledger and whether its holder
  process is alive, and suggest the right verb instead of sending the
  operator to the filesystem.
- Drafts should not be able to hold a GLOBAL lease (`.git/frob-leases/`,
  visible from every worktree) for a ticket that exists only in ONE
  worktree's LOCAL ledger. That asymmetry is the actual root cause
  behind shape 2 -- the lease outlives the only place its ticket is
  recorded, so nothing global can ever resolve it by id. Either promote
  the draft at lease-record time, or scope the lease to the same place
  the ticket actually lives.

Cross-references: T-1789 (path-orphan detection/release, the mechanism
this generalizes); T-1779 (the root-checkout-write-guard family this is
the same "no scoped verb" pattern from).
