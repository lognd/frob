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
milestone: 1.1.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.538.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: v0.538.0
  new_value: v1.1.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer F-357/H4-5 (T-4157): optional interface methods make an incomplete implementation type-legal, so nothing at build or check time notices a fallback adapter implementing only 6 of 9 declared members. High-value generic mechanism, not domain-specific to the consumer's renderer. Fixture-testable: YES, frob's own Protocol/ABC-shaped ports with multiple implementations (e.g. gate registration interfaces) are a real fixture.