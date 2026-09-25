---
id: T-5351
title: 'WEBSEC201-208: CSRF and session lifecycle'
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
worktree: /home/logan/projects/frob/.claude/worktrees/t-5351
branch: t-5351
scope:
- src/frob/webapp/_websec_csrf_session.py
- tests/fixtures/webapp/websec2xx/csrf_session/**
- tests/unit/test_websec_csrf_session.py
- docs/modules/webapp-websec-csrf-session.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/fixtures/webapp/websec2xx/**
  reason: per-ticket fixture subdir so the session/auth leaves do not lease-collide
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/fixtures/webapp/websec2xx/csrf_session/**
  reason: per-ticket fixture subdir so the session/auth leaves do not lease-collide
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/unit/test_websec_csrf_session.py
  reason: unit test + doc for the new module, per playbook convention
  actor: logan
  at: '2026-09-24'
- op: add
  glob: docs/modules/webapp-websec-csrf-session.md
  reason: unit test + doc for the new module, per playbook convention
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
  at: '2026-09-24'
evidence:
- tests/unit/test_websec_csrf_session.py::test_taint_gate_discovers_websec_csrf_session_hook
- tests/unit/test_websec_csrf_session.py::test_websec_csrf_session_findings_fixture[webesc201_positive-WEBSEC201-True]
- tests/unit/test_websec_csrf_session.py::test_websec_csrf_session_findings_fixture[webesc201_negative-WEBSEC201-False]
- tests/unit/test_websec_csrf_session.py::test_websec_csrf_session_findings_fixture[webesc202_positive-WEBSEC202-True]
- tests/unit/test_websec_csrf_session.py::test_websec_csrf_session_findings_fixture[webesc202_negative-WEBSEC202-False]
- tests/unit/test_websec_csrf_session.py::test_websec_csrf_session_findings_fixture[webesc203_positive-WEBSEC203-True]
- tests/unit/test_websec_csrf_session.py::test_websec_csrf_session_findings_fixture[webesc203_negative-WEBSEC203-False]
- tests/unit/test_websec_csrf_session.py::test_websec_csrf_session_findings_fixture[webesc204_positive-WEBSEC204-True]
- tests/unit/test_websec_csrf_session.py::test_websec_csrf_session_findings_fixture[webesc204_negative-WEBSEC204-False]
- tests/unit/test_websec_csrf_session.py::test_websec_csrf_session_findings_fixture[webesc205_positive-WEBSEC205-True]
- tests/unit/test_websec_csrf_session.py::test_websec_csrf_session_findings_fixture[webesc205_negative-WEBSEC205-False]
- tests/unit/test_websec_csrf_session.py::test_websec_csrf_session_findings_fixture[webesc206_positive-WEBSEC206-True]
- tests/unit/test_websec_csrf_session.py::test_websec_csrf_session_findings_fixture[webesc206_negative-WEBSEC206-False]
- tests/unit/test_websec_csrf_session.py::test_websec_csrf_session_findings_fixture[webesc207_positive-WEBSEC207-True]
- tests/unit/test_websec_csrf_session.py::test_websec_csrf_session_findings_fixture[webesc207_negative-WEBSEC207-False]
- tests/unit/test_websec_csrf_session.py::test_websec_csrf_session_findings_fixture[webesc208_positive-WEBSEC208-True]
- tests/unit/test_websec_csrf_session.py::test_websec_csrf_session_findings_fixture[webesc208_negative-WEBSEC208-False]
- tests/unit/test_websec_csrf_session.py::test_websec_csrf_session_findings_no_framework_short_circuits
- tests/unit/test_websec_csrf_session.py::test_websec_findings_discovery_hook_emits_violation
- tests/unit/test_websec_csrf_session.py::test_websec_findings_discovery_hook_empty_frameworks_short_circuits
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
State-changing GET requests, missing CSRF middleware, SameSite cookie default, client-only session-validity check, no session-id rotation on login, idle timeout config, absolute session lifetime config, logout server-side invalidation, plus the static half of account-enumeration-via-error-text. Route-table AST lint for the handler-shape rules, SessionConfig (5142-1) for the config rules. Fixture per rule id.