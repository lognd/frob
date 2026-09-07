---
id: T-4220
title: 'purity/ownership invariant: a controller documented Pure must not be wired
  to a caller that writes its output back into the buffers it read'
state: queued
kind: feature
origin: agent
created: '2026-09-07'
priority: low
parent: T-4157
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_inv.py
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
Consumer F-357/H4-8 (T-4157): a controller documented 'Pure: reads world, never mutates it' is wired to a caller that applies its outputs to the same buffers it read, mutating real state despite the documented contract. A general purity/ownership rule is beyond current gates; the practical version is a frob:invariant on the caller's state at a defined checkpoint, bound to a test. Fixture-testable: mechanism is generic and partially testable with a synthetic pure-function fixture in frob's own tree; the consumer's specific attract-mode domain does not exist here.