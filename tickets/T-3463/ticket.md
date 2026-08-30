---
id: T-3463
title: 'TICK004: consider rot-checking a decomposed epic against its children''s own
  progress'
state: queued
kind: feature
origin: human
created: '2026-08-30'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_tickets_gate.py
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
Found while working T-3399.

T-3399 capped TICK004's severity at WARN for a decomposed epic/story
(has at least one non-terminal child) instead of letting age alone
escalate it to ERROR -- the false-positive fix for three genuinely
healthy epics.

T-3399's body explicitly raised, and deferred, a sharper question:
should a decomposed epic's rot be measured against its CHILDREN's own
progress instead of (or in addition to) its own age? An epic whose
children are ALL ALSO stalled really is rotting -- that would be a
more precise finding than the current flat WARN cap, which stays
silent about whether the children themselves are healthy.

Candidate shape: for a decomposed epic/story, instead of (or in
addition to) the epic's own age, compute the age of its OLDEST
non-terminal child and rot-check THAT against the child's own
priority threshold -- if even the newest active child is itself
stalled, escalate. Needs its own design pass (recursive descent for
nested epics, calibration against real ledger data, and a decision on
what message/severity that finding should carry) rather than a
one-line change to _tick004_queue_rot.
