---
id: T-draft-0f5b1a08
title: 'WEBSEC326-334: logging, timeouts, resource limits'
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
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/webapp/_websec_logging_limits.py
- tests/fixtures/webapp/websec3xx/**
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
Auth-event audit logging (V16.3.1/V16.3.2), log metadata completeness + UTC timestamps, PII in logs (extends 5143-3's secret-pattern reuse with a PII field-name denylist), log-retention policy (config), outbound HTTP client timeout missing, request body size limit missing, server request timeout (config), GraphQL introspection/depth limit (config), least-functionality (debug/test routes in prod route table), outbound egress allowlist (config), client storage cleared on logout. WebSocket origin check is owned by T-5141-4, NOT this leaf -- cross-reference its rule id instead of reimplementing. Fixture per rule id.