---
id: T-4245
title: 'SYS/REL: require a timeout attribute on every net.connect/fetch_url strata
  grant, and flag a grant that declares none'
state: queued
kind: feature
origin: agent
created: '2026-09-07'
priority: medium
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
Consumer F-326/M2-1: strata has vocabulary for a component's own explicit timeout obligation, but a bare may net.connect via <file> grant carries no obligation of its own, so a capability can be added with no timeout at all. A one-line model change with repo-wide reach. Fixture-testable: YES if frob's own design/frob.strata carries net.connect-shaped grants; otherwise partial.