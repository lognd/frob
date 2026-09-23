---
id: T-5354
title: 'WEBSEC226-230: randomness and TLS verification'
state: queued
kind: feature
origin: human
created: '2026-09-23'
priority: high
parent: T-5142
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: 3
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/webapp/_websec_crypto_tls.py
- tests/fixtures/webapp/websec2xx/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '3'
  new_value: '3'
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
Math.random()/random.random() used for a token/session-id/API-key/CSRF-token (name-based heuristic on the assignment target, PERF-family lexical-smell precedent), TLS verification disabled (requests verify=False/rejectUnauthorized:false/literal http:// to an API), TLS minimum version config, certificate pinning (mobile-only, config advisory), credential-stuffing rate-limit cross-refs 5144-2's rate-limit rule. HSTS is owned by T-5143-2's header-lint substrate, NOT this leaf -- this leaf blocks on it rather than reimplementing header parsing. Fixture per rule id.