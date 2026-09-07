---
id: T-4192
title: 'route-inventory check: a handler returning a dict/mapping literal response
  must declare a response model'
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
Consumer F-307/H3-7 (T-4109): COV/WIRE see the response type as referenced because some routes use it, masking routes returning a bare dict literal instead. Same family as the existing SIT-011 guard-inventory pattern. Not fixture-testable in frob's own tree: no HTTP routes exist here. Consumer-blocking: latent for us.