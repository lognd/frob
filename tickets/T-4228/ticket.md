---
id: T-4228
title: 'coverage-over-a-registry is not coverage-over-the-real-surface: add a surface-enumeration
  check alongside registry-totality tests'
state: queued
kind: feature
origin: agent
created: '2026-09-07'
priority: medium
parent: T-4175
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
Consumer F-373/P4 (T-4175): a totality test proves every registered error-set member has an HTTP mapping -- a claim about the registry, not about the response surface. Nothing enumerates the error responses the framework itself can actually produce. Rule: fire one deliberately malformed request at each real route in the app's route table and assert the envelope, alongside the registry-totality test. Same shape as frob's own risk (a gate registered in one list and absent from another) named across this session's own drives. Not fixture-testable in frob's own tree: no HTTP route table exists here.