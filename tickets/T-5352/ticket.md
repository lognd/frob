---
id: T-5352
title: 'WEBSEC209-217: JWT and OAuth token checks'
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
- src/frob/webapp/_websec_tokens.py
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
JWT exp/nbf validation, aud validation, iss/token-type confusion, refresh-token rotation+absolute-TTL (config), tokens leaked via URL query/fragment, OAuth state parameter, redirect_uri exact-match (config), PKCE on the authorization-code flow. Secrets-committed cross-refs SEC001-003, not duplicated. AST lint on jwt.decode/jsonwebtoken.verify call-argument presence; OAuth-client call-argument AST. Fixture per rule id.