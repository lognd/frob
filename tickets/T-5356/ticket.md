---
id: T-5356
title: 'WEBSEC authz substrate: route/handler ownership-check AST walker'
state: in-progress
kind: feature
origin: human
created: '2026-09-23'
priority: high
blocked_by:
- T-5302
parent: T-5144
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
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
- src/frob/webapp/_websec_authz_substrate.py
- tests/fixtures/webapp/websec4xx/**
- tests/unit/test_webapp_websec_authz_substrate.py
- docs/modules/webapp-websec-authz.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_webapp_websec_authz_substrate.py
  reason: unit test for the new substrate module, required to bind frob:tests evidence
  actor: logan
  at: '2026-09-23'
- op: add
  glob: docs/modules/webapp-websec-authz.md
  reason: module doc for the new substrate, cited via frob:doc, sibling family docs
    stay out of the shared webapp.md
  actor: logan
  at: '2026-09-23'
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
worktree: /home/logan/projects/frob/.claude/worktrees/t-5356
branch: t-5356
---
Per-framework route-table extraction (Flask/FastAPI/Express/Django/Rails route decorators/registrations) plus a body-AST walk for an ORM filter/where clause referencing the authenticated user id -- ships as a documented heuristic (current_user/request.user/g.user identifier present, correlated with the ORM lookup call), not a sound analysis, same posture as PERF008's loop-invariant-effect heuristic. Fixture: one handler with the owner filter (clean) and one without (planted finding) per framework.