---
id: T-3378
title: 'TICK002 re-raise self-deadlocks the fleet: draft-id quarantine only clears
  via a land it blocks'
state: in-progress
kind: bug
origin: human
created: '2026-08-29'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/verify/**
- src/frob/tickets/_draft_finalize.py
- src/frob/gates/_tick_directives.py
- tests/unit/verify/test_quarantine.py
- frob.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/verify/test_quarantine.py
  reason: T-3378 adds unit tests for the new TICK002/draft-owner exemption filter,
    and frob ack writes frob.lock as part of acknowledging the resulting DRIFT001
  actor: logan
  at: '2026-08-29'
- op: add
  glob: frob.lock
  reason: T-3378 adds unit tests for the new TICK002/draft-owner exemption filter,
    and frob ack writes frob.lock as part of acknowledging the resulting DRIFT001
  actor: logan
  at: '2026-08-29'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Observed during T-2667's land (2026-08-29, ~load 59, 10+ concurrent
series landing): TICK002 fires when a `T-draft-*` id survives onto the
default branch. Our close-time mirroring writes in-progress ticket
files (including their T-draft-* ids) onto main BEFORE the owning
ticket lands and gets renumbered -- so TICK002 fires on every in-flight
draft BY CONSTRUCTION, not as a genuine anomaly.

A raised quarantine turns deferred landing OFF repo-wide (T-1693) and
forces fully-synchronous verification on EVERY land in the fleet. So:

  land blocked by quarantine
    -> quarantine raised by a T-draft-* id on main
    -> that id only finalizes (clearing the condition) when ITS
       OWNING ticket lands
    -> but every land, including the owning ticket's, is blocked by
       the same quarantine

This is a design-level deadlock, not a tuning problem. It surfaced
twice in one drive (2026-08-29): the coordinator dismissed the
TICK002@tickets.md finding twice (recorded reasoning: the two
surviving ids, T-draft-1b6f3c6d and T-draft-547b0587, were legitimately
in-progress with live/owning series), and the quarantine re-raised
within the same session both times, at batch shas
983851e929ced4200670c0b3e2381553caedb5ec and
a5b80af0e8b8919eb712b2e437f32a5567a438eb (verify worker re-detected
the still-true condition on its next wake). The cycle only broke when
one of the two owning series's land happened to get through on its
own -- not because the dismissal fixed anything.

Under a large fleet (10+ concurrent series), this is a live lock that
can stall the entire land pipeline for extended periods (observed
~40+ minutes of failed/timed-out land attempts across multiple series
during this window) with no route out except waiting for an unrelated
land to happen to succeed.

Candidate fixes (not decided here, just naming the shape of the
options for whoever picks this up): (a) TICK002 should not count a
T-draft-* id that has a live/owning in-progress ticket against it
(mirrors the coordinator's own dismissal reasoning, i.e. encode it as
a real exemption instead of a per-incident manual dismiss); (b) close-
time mirroring should not write draft ids to main at all, only after
promotion; (c) quarantine-raised-by-TICK002-on-a-draft-id specifically
should not force synchronous verification fleet-wide, since by
definition it cannot be resolved by any land other than the specific
one holding that draft's lease.
