---
id: T-4250
title: 'strata flow-participation: a shared contract implemented by more than one
  component must have both declare participation in one flow node'
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
Consumer F-327/M-6: two components each implement half of a single logical contract (an unauthenticated-redirect flow) with no cross-reference between their spec anchors, so they can diverge silently. Declare a strata flow node that both must declare participation in, so frob sys audit reports two participants implementing the same flow with divergent behaviour. Not fixture-testable in frob's own tree: no such multi-component flow-contract shape exists here.