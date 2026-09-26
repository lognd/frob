---
id: T-5357
title: 'WEBSEC401-407: route-level authorization (admin routes, IDOR/BOLA, mass assignment,
  pagination)'
state: done
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
flavour: null
due: null
rank: null
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
- docs/modules/webapp-websec-authz-routes.md
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
- op: add
  glob: docs/modules/webapp-websec-authz-routes.md
  reason: module doc, per T-5325-family convention
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
evidence:
- tests/unit/test_websec_authz_routes.py::test_websec_authz_route_findings_fixture[webesc401_positive-WEBSEC401-True]
- tests/unit/test_websec_authz_routes.py::test_websec_authz_route_findings_fixture[webesc401_negative-WEBSEC401-False]
- tests/unit/test_websec_authz_routes.py::test_websec_authz_route_findings_fixture[webesc402_positive-WEBSEC402-True]
- tests/unit/test_websec_authz_routes.py::test_websec_authz_route_findings_fixture[webesc402_negative-WEBSEC402-False]
- tests/unit/test_websec_authz_routes.py::test_websec_authz_route_findings_fixture[webesc403_positive-WEBSEC403-True]
- tests/unit/test_websec_authz_routes.py::test_websec_authz_route_findings_fixture[webesc403_negative-WEBSEC403-False]
- tests/unit/test_websec_authz_routes.py::test_websec_authz_route_findings_fixture[webesc404_positive-WEBSEC404-True]
- tests/unit/test_websec_authz_routes.py::test_websec_authz_route_findings_fixture[webesc404_negative-WEBSEC404-False]
- tests/unit/test_websec_authz_routes.py::test_websec_authz_route_findings_fixture[webesc405_positive-WEBSEC405-True]
- tests/unit/test_websec_authz_routes.py::test_websec_authz_route_findings_fixture[webesc405_negative-WEBSEC405-False]
- tests/unit/test_websec_authz_routes.py::test_websec_authz_route_findings_fixture[webesc406_positive-WEBSEC406-True]
- tests/unit/test_websec_authz_routes.py::test_websec_authz_route_findings_fixture[webesc406_negative-WEBSEC406-False]
- tests/unit/test_websec_authz_routes.py::test_websec_authz_route_findings_fixture[webesc407_positive-WEBSEC407-True]
- tests/unit/test_websec_authz_routes.py::test_websec_authz_route_findings_fixture[webesc407_negative-WEBSEC407-False]
- tests/unit/test_websec_authz_routes.py::test_websec_authz_route_findings_no_framework_short_circuits
- tests/unit/test_websec_authz_routes.py::test_websec_findings_discovery_hook_emits_violation
- tests/unit/test_websec_authz_routes.py::test_websec_findings_discovery_hook_empty_frameworks_short_circuits
- tests/unit/test_websec_authz_routes.py::test_taint_gate_discovers_websec_authz_routes_hook
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Admin routes without the framework's auth decorator/middleware, front-end-only permission guards (React router-guard AST cross-referenced against the server route table), IDOR/BOLA (5144-1 substrate), mass assignment (request.json/params passed whole to create/update), field-level over-exposure, list-endpoint pagination -- this rule is the canonical owner of list-endpoint-pagination; T-5147-6 (WEBPERF) blocks on this leaf instead of reimplementing the pagination check. Per-user rate limiting on auth/expensive endpoints. Fixture per rule id.