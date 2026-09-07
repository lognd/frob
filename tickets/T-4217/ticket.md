---
id: T-4217
title: 'interface/adapter parity: every optional member of an invariant-marked port
  must be implemented by every adapter, or the adapter must declare the omission'
state: queued
kind: feature
origin: agent
created: '2026-09-07'
priority: high
parent: T-4157
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates
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
Consumer F-357/H4-5 (T-4157): optional interface methods make an incomplete implementation type-legal, so nothing at build or check time notices a fallback adapter implementing only 6 of 9 declared members. High-value generic mechanism, not domain-specific to the consumer's renderer. Fixture-testable: YES, frob's own Protocol/ABC-shaped ports with multiple implementations (e.g. gate registration interfaces) are a real fixture.