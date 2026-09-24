---
id: T-5357
title: 'WEBSEC401-407: route-level authorization (admin routes, IDOR/BOLA, mass assignment,
  pagination)'
state: in-progress
kind: feature
origin: human
created: '2026-09-23'
priority: high
blocked_by:
- T-5356
parent: T-5144
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
worktree: /home/logan/projects/frob/.claude/worktrees/t-5357
branch: t-5357
scope:
- src/frob/webapp/_websec_authz_routes.py
- tests/fixtures/webapp/websec4xx/routes/**
- tests/unit/test_websec_authz_routes.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/fixtures/webapp/websec4xx/**
  reason: per-ticket fixture subdir, sibling T-5359 owns the rest of websec4xx
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/fixtures/webapp/websec4xx/routes/**
  reason: per-ticket fixture subdir, sibling T-5359 owns the rest of websec4xx
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/unit/test_websec_authz_routes.py
  reason: unit test file, per T-5325-family convention
  actor: logan
  at: '2026-09-24'
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
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Admin routes without the framework's auth decorator/middleware, front-end-only permission guards (React router-guard AST cross-referenced against the server route table), IDOR/BOLA (5144-1 substrate), mass assignment (request.json/params passed whole to create/update), field-level over-exposure, list-endpoint pagination -- this rule is the canonical owner of list-endpoint-pagination; T-5147-6 (WEBPERF) blocks on this leaf instead of reimplementing the pagination check. Per-user rate limiting on auth/expensive endpoints. Fixture per rule id.