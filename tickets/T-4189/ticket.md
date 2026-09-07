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
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata
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
Consumer F-307/H3-2 (T-4109): retention is a time bound, not a rate bound; nothing models write amplification on carries-bearing stores. Mirror the existing outbound-flow rate requirement onto inbound writes. Not fixture-testable in frob's own tree: no carries/PII-bearing store or unauthenticated-route model exists here. Consumer-blocking: latent for us; was live for the consumer.