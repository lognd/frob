---
id: T-2576
title: 'M2: backfill open tickets to 1.0.0, add MILE003 gate'
state: in-progress
kind: feature
origin: human
created: '2026-08-18'
priority: high
blocked_by:
- T-2574
parent: T-2573
tier: ticket
sprint: null
runs_last: false
milestone: null
scope:
- src/frob/gates/_milestone.py
- src/frob/gates/__init__.py
- src/frob/tickets/_doable.py
- src/frob/app/ticket_runner/_query.py
- docs/modules/tickets-data-storage.md
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tickets.md
  reason: tickets.md and tickets-archive.md were deleted in the ledger-v2 cutover
    (T-1258/T-2356) and are neither on disk nor tracked; the backfill's real target
    is the per-ticket v2 files
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: tickets-archive.md
  reason: tickets.md and tickets-archive.md were deleted in the ledger-v2 cutover
    (T-1258/T-2356) and are neither on disk nor tracked; the backfill's real target
    is the per-ticket v2 files
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tickets/T-*/ticket.md
  reason: tickets.md and tickets-archive.md were deleted in the ledger-v2 cutover
    (T-1258/T-2356) and are neither on disk nor tracked; the backfill's real target
    is the per-ticket v2 files
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: tickets/T-*/ticket.md
  reason: 'repo-wide ledger lease removed: read-time default replaces the bulk backfill
    (coordinator review, T-2593 class)'
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/tickets/_doable.py
  reason: 'T-2576 redesign: extend M3''s effective_milestone() with configured default
    as terminal fallback (single home for resolution), and doable render needs a third
    DEFAULTED case distinct from declared/inherited'
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/app/ticket_runner/_query.py
  reason: 'T-2576 redesign: extend M3''s effective_milestone() with configured default
    as terminal fallback (single home for resolution), and doable render needs a third
    DEFAULTED case distinct from declared/inherited'
  actor: logan
  at: '2026-08-19'
- op: add
  glob: docs/modules/tickets-data-storage.md
  reason: 'T-2576 redesign: extend M3''s effective_milestone() with configured default
    as terminal fallback (single home for resolution), and doable render needs a third
    DEFAULTED case distinct from declared/inherited'
  actor: logan
  at: '2026-08-19'
- op: add
  glob: docs/modules/tickets.md
  reason: 'T-2576 redesign: extend M3''s effective_milestone() with configured default
    as terminal fallback (single home for resolution), and doable render needs a third
    DEFAULTED case distinct from declared/inherited'
  actor: logan
  at: '2026-08-19'
body_changes:
- mode: append
  reason: 'remove the repo-wide ledger lease: read-time default replaces the bulk
    backfill, unblocking M4'
  actor: logan
  at: '2026-08-19'
  old_length: 1171
  new_length: 4763
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Two parts, both required for this ticket to be complete:

1. Backfill: stamp `milestone: 1.0.0` into every currently OPEN ticket
   (state in _OPEN_STATES -- roughly 83 tickets as of 2026-08-17, will
   have moved by implementation time; re-measure, do not hardcode the
   count). Do NOT touch terminal (done/dropped) tickets -- they never
   sequence again and backfilling them is wasted churn.

2. MILE003 (ERROR): an OPEN ticket with no milestone set. This is what
   stops new tickets silently skipping the field after M1 adds it.
   MILE003 must distinguish "no milestone declared" (a real finding) from
   "could not read the queue" (a measurement failure) -- a queue-load
   failure must NOT render as zero findings. Follow the same
   fail-loud-on-load-failure shape other gates in this repo already use;
   do not invent a new pattern.

Depends on M1 (T-2574) for the `milestone` field and setter to exist.
Explicitly out of scope: _doable_sort_key changes (M3), runs_last
rescoping (M4/M4b), MILE001/MILE002 (M5), REL001 (M6).

Positive control: MILE003 must fire on a planted OPEN ticket with no
milestone, and must NOT fire once that ticket is stamped 1.0.0.


## SCOPE REDESIGN -- the bulk backfill is removed from this ticket

Coordinator review, 2026-08-19. As originally written this ticket declared
`tickets/T-*/ticket.md` in scope: a write lease on EVERY ticket file.

Scope IS the write lease here, and every working agent writes its own
ticket file constantly (evidence, Done report, state transitions). So this
ticket as specified could only run with the entire fleet stopped, and it
sat blocking M4 -- which is what finally makes T-1614 reachable, an alarm
now 14 days old. It also repeats, in the ledger, exactly the over-broad
ownership claim filed as T-2593.

**The backfill is not actually necessary.** Its only purpose was to give
every open ticket a milestone so sequencing and MILE003 have something to
read. A read-time default achieves the identical result with no writes:

- Add a `default_milestone` setting (`1.0.0` for this repo) to config.
- Extend effective-milestone resolution with it as the TERMINAL fallback:
  own declared value, else nearest ancestor's (story, then epic), else the
  configured default.
- MILE003 then fires when a ticket's effective milestone cannot be
  RESOLVED -- e.g. no declared value anywhere in the chain and no
  configured default -- rather than when a field is literally absent.

Net effect: 89 ticket files stay untouched, no ledger-wide lease, no
quiet window, and M4 unblocks immediately.

## Revised scope for this ticket

    src/frob/gates/_milestone.py
    src/frob/gates/__init__.py
    plus the config surface for `default_milestone`

Explicitly NOT `tickets/T-*/ticket.md`. Do not bulk-edit ticket files.

## Coordination -- read this before you start

M3 (T-2577) is IN FLIGHT and owns effective-milestone resolution for the
`doable` sort (own value, else nearest ancestor). Do NOT reimplement that
chain. Your job is to add the configured default as the terminal fallback
to whatever M3 lands, and to build MILE003 on top of it. If M3 has not
landed when you start, coordinate rather than racing it -- the resolution
function must have exactly ONE home.

## The distinguishability requirement carries over unchanged

M3 already requires that an INHERITED milestone render visibly distinct
from a DECLARED one. The configured default is a third case and must be
distinguishable from both. "Defaulted because nobody chose" and "explicitly
set to 1.0.0" are different facts, and collapsing them is the silent-zero
pattern this epic exists to avoid: a value that merely LOOKS decided.

MILE003 must likewise distinguish "no milestone resolvable" from "could not
read the queue". A queue-load failure must never render as zero findings.

## Optional cleanup, deliberately NOT in this ticket

Stamping literal `milestone: 1.0.0` into the 89 open tickets is now
cosmetic rather than load-bearing. If it is ever wanted, it is a separate
low-priority ticket run in a genuinely quiet window with no agents active.
File it if you think it is worth doing; do not do it here.

## Positive controls, both directions

- an open ticket with no declared milestone and no milestoned ancestor
  resolves to the configured default, and `doable` shows it as DEFAULTED,
  not as declared
- a ticket with a declared milestone keeps it -- the default must not
  override a real value
- a ticket inheriting from an ancestor still shows INHERITED, unchanged
  from M3
- with no `default_milestone` configured, MILE003 FIRES rather than
  silently assuming 1.0.0. Without this case the default is just a way to
  make the gate never fire
- a queue that cannot be loaded reports an ERROR, never zero findings