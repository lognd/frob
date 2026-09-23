---
id: T-5356
title: 'WEBSEC authz substrate: route/handler ownership-check AST walker'
state: queued
kind: feature
origin: human
created: '2026-09-23'
priority: high
parent: T-5144
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: 5
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/webapp/_websec_authz_substrate.py
- tests/fixtures/webapp/websec4xx/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Per-framework route-table extraction (Flask/FastAPI/Express/Django/Rails route decorators/registrations) plus a body-AST walk for an ORM filter/where clause referencing the authenticated user id -- ships as a documented heuristic (current_user/request.user/g.user identifier present, correlated with the ORM lookup call), not a sound analysis, same posture as PERF008's loop-invariant-effect heuristic. Fixture: one handler with the owner filter (clean) and one without (planted finding) per framework.