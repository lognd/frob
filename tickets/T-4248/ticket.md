---
id: T-4248
title: 'first-class (( ratchet )) declaration primitive: baseline path, producing
  command, subset-only semantics, required ticket to grow'
state: queued
kind: feature
origin: agent
created: '2026-09-07'
priority: low
parent: T-4135
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_ratchet.py
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
Consumer F-326/M2-9: frob has ratchet machinery (SYS111, this repo's own baseline files) but no general 'declare a tolerated set that may only shrink' primitive, so each is hand-rolled with different semantics -- and a genuinely tolerated set (their PLANNED runnables) simply never got one. A first-class (( ratchet )) declaration would let this repo's own several baselines share one implementation and one contract. Fixture-testable: YES, frob's own SYS111 and baseline-file mechanisms are real first adopters.