---
id: T-5351
title: 'WEBSEC201-208: CSRF and session lifecycle'
state: queued
kind: feature
origin: human
created: '2026-09-22'
priority: high
blocked_by:
- T-5349
parent: T-5142
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
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
- src/frob/webapp/_websec_csrf_session.py
- tests/fixtures/webapp/websec2xx/**
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
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
State-changing GET requests, missing CSRF middleware, SameSite cookie default, client-only session-validity check, no session-id rotation on login, idle timeout config, absolute session lifetime config, logout server-side invalidation, plus the static half of account-enumeration-via-error-text. Route-table AST lint for the handler-shape rules, SessionConfig (5142-1) for the config rules. Fixture per rule id.