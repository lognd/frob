---
id: T-2576
title: 'M2: backfill open tickets to 1.0.0, add MILE003 gate'
state: queued
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
scope:
- src/frob/gates/_milestone.py
- src/frob/gates/__init__.py
- tickets.md
- tickets-archive.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
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
