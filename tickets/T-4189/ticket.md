---
id: T-4189
title: 'strata: require a rate attribute on inbound writes to a carries-bearing store
  from an unauthenticated route'
state: queued
kind: feature
origin: agent
created: '2026-09-07'
priority: medium
parent: T-4109
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
- src/frob/strata
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
Consumer F-307/H3-2 (T-4109): retention is a time bound, not a rate bound; nothing models write amplification on carries-bearing stores. Mirror the existing outbound-flow rate requirement onto inbound writes. Not fixture-testable in frob's own tree: no carries/PII-bearing store or unauthenticated-route model exists here. Consumer-blocking: latent for us; was live for the consumer.