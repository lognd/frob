---
id: T-5352
title: 'WEBSEC209-217: JWT and OAuth token checks'
state: done
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
worktree: /home/logan/projects/frob/.claude/worktrees/t-5352
branch: t-5352
scope:
- src/frob/webapp/_websec_tokens.py
- tests/fixtures/webapp/websec2xx/jwt_oauth/**
- tests/unit/test_websec_tokens.py
- docs/modules/webapp-websec-jwt-oauth.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/fixtures/webapp/websec2xx/**
  reason: per-ticket fixture subdir, sibling T-5351 owns csrf_session/**
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/fixtures/webapp/websec2xx/jwt_oauth/**
  reason: per-ticket fixture subdir, sibling T-5351 owns csrf_session/**
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/unit/test_websec_tokens.py
  reason: unit test file, per T-5325-family convention
  actor: logan
  at: '2026-09-24'
- op: add
  glob: docs/modules/webapp-websec-jwt-oauth.md
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
  at: '2026-09-24'
evidence:
- tests/unit/test_websec_tokens.py::test_websec_token_findings_fixture[webesc209_positive-WEBSEC209-True]
- tests/unit/test_websec_tokens.py::test_websec_token_findings_fixture[webesc209_negative-WEBSEC209-False]
- tests/unit/test_websec_tokens.py::test_websec_token_findings_fixture[webesc210_positive-WEBSEC210-True]
- tests/unit/test_websec_tokens.py::test_websec_token_findings_fixture[webesc210_negative-WEBSEC210-False]
- tests/unit/test_websec_tokens.py::test_websec_token_findings_fixture[webesc211_positive-WEBSEC211-True]
- tests/unit/test_websec_tokens.py::test_websec_token_findings_fixture[webesc211_negative-WEBSEC211-False]
- tests/unit/test_websec_tokens.py::test_websec_token_findings_fixture[webesc212_positive-WEBSEC212-True]
- tests/unit/test_websec_tokens.py::test_websec_token_findings_fixture[webesc212_negative-WEBSEC212-False]
- tests/unit/test_websec_tokens.py::test_websec_token_findings_fixture[webesc213_positive-WEBSEC213-True]
- tests/unit/test_websec_tokens.py::test_websec_token_findings_fixture[webesc213_negative-WEBSEC213-False]
- tests/unit/test_websec_tokens.py::test_websec_token_findings_fixture[webesc214_positive-WEBSEC214-True]
- tests/unit/test_websec_tokens.py::test_websec_token_findings_fixture[webesc214_negative-WEBSEC214-False]
- tests/unit/test_websec_tokens.py::test_websec_token_findings_fixture[webesc215_positive-WEBSEC215-True]
- tests/unit/test_websec_tokens.py::test_websec_token_findings_fixture[webesc215_negative-WEBSEC215-False]
- tests/unit/test_websec_tokens.py::test_websec_token_findings_fixture[webesc216_positive-WEBSEC216-True]
- tests/unit/test_websec_tokens.py::test_websec_token_findings_fixture[webesc216_negative-WEBSEC216-False]
- tests/unit/test_websec_tokens.py::test_websec_token_findings_no_framework_short_circuits
- tests/unit/test_websec_tokens.py::test_websec_findings_discovery_hook_emits_violation
- tests/unit/test_websec_tokens.py::test_websec_findings_discovery_hook_empty_frameworks_short_circuits
- tests/unit/test_websec_tokens.py::test_taint_gate_discovers_websec_tokens_hook
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
JWT exp/nbf validation, aud validation, iss/token-type confusion, refresh-token rotation+absolute-TTL (config), tokens leaked via URL query/fragment, OAuth state parameter, redirect_uri exact-match (config), PKCE on the authorization-code flow. Secrets-committed cross-refs SEC001-003, not duplicated. AST lint on jwt.decode/jsonwebtoken.verify call-argument presence; OAuth-client call-argument AST. Fixture per rule id.