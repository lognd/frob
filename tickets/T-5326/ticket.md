---
id: T-5326
title: 'WEBSEC301-309: security headers (CSP/HSTS/COOP/CORP/CORS/Cache-Control)'
state: queued
kind: feature
origin: human
created: '2026-09-22'
priority: high
parent: T-5143
tier: ticket
sprint: v0.536.0
runs_last: false
milestone: null
points: 5
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/webapp/_websec_headers_rules.py
- tests/fixtures/webapp/websec3xx/**
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
  at: '2026-09-22'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CSP w/ nonce (ASVS V3.4.3), HSTS max-age>=31536000 (V3.4.1/V3.7.4), X-Content-Type-Options nosniff (V3.4.4), Referrer-Policy (V3.4.5), Permissions-Policy, COOP/COEP/CORP, CORS fixed/allowlisted origin (V3.4.2), CORS-preflight-reliance for sensitive functionality (V3.5.1/V3.5.2), Cache-Control no-store on authenticated responses (V14.3.2) -- this rule is the canonical owner of Cache-Control-on-authenticated-responses; T-5147-6 (WEBPERF server/network) blocks on this leaf rather than reimplementing the authenticated-route detection. Cache-key poisoning ships as a WARN advisory only (no ASVS id found in the corpus). Fixture per rule id via 5143-1.