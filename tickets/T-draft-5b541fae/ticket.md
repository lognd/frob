---
id: T-draft-5b541fae
title: 'WEBSEC401-407: route-level authorization (admin routes, IDOR/BOLA, mass assignment,
  pagination)'
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
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/webapp/_websec_authz_routes.py
- tests/fixtures/webapp/websec4xx/**
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
Admin routes without the framework's auth decorator/middleware, front-end-only permission guards (React router-guard AST cross-referenced against the server route table), IDOR/BOLA (5144-1 substrate), mass assignment (request.json/params passed whole to create/update), field-level over-exposure, list-endpoint pagination -- this rule is the canonical owner of list-endpoint-pagination; T-5147-6 (WEBPERF) blocks on this leaf instead of reimplementing the pagination check. Per-user rate limiting on auth/expensive endpoints. Fixture per rule id.