---
id: T-2580
title: 'M5: MILE001/MILE002 milestone-deadlock gates'
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
Two gates, both ERROR:

- MILE001: a ticket `blocked_by` a ticket in a LATER milestone. This is
  a provable release deadlock -- the earlier milestone can never ship
  while it depends on work the later milestone hasn't done yet.
- MILE002: an epic/story whose descendant is in a LATER milestone. Same
  deadlock via the hierarchy, since `_done_transition_guard` already
  forbids closing an epic over an open descendant (verified: this guard
  already exists) -- MILE002 is that same rule projected onto
  milestones, catching it statically before close-time.

Both need positive controls in BOTH directions:
- a planted MILE001/MILE002 violation must FIRE.
- a legitimate same-milestone edge, or an edge where the blocker is in
  an EARLIER milestone, must NOT fire.

Register both in `_KNOWN_GATE_RULES` so `frob:waive MILE001`/
`frob:waive MILE002` bind correctly, and add them to that list's
`frob:enumerates` member set so DOCENUM001 stays clean -- find the
existing member set by name first (do not guess its location or
reinvent a second registry).

Depends on M1 (T-2574, field must exist) only. Does not depend on
M2/M3/M4/M4b -- these are static ledger-shape checks over `milestone`
and `blocked_by`/`parent`, independent of doable ordering or runs_last
semantics.
