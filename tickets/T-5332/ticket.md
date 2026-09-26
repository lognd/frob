---
id: T-5332
title: 'WEBSEC326-334: logging, timeouts, resource limits'
state: done
kind: feature
origin: human
created: '2026-09-22'
priority: high
blocked_by:
- T-5325
parent: T-5143
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
flavour: null
points: 5
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5332
branch: t-5332
scope:
- src/frob/webapp/_websec_logging_limits.py
- tests/fixtures/webapp/websec3xx/logging/**
- tests/unit/test_websec_logging_limits.py
- docs/modules/webapp-websec-logging-limits.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/fixtures/webapp/websec3xx/**
  reason: per-ticket fixture subdir so the four headers leaves do not lease-collide
    on the shared glob
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/fixtures/webapp/websec3xx/logging/**
  reason: per-ticket fixture subdir so the four headers leaves do not lease-collide
    on the shared glob
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/unit/test_websec_logging_limits.py
  reason: unit test for the new module, standard test-file scope companion
  actor: logan
  at: '2026-09-24'
- op: add
  glob: docs/modules/webapp-websec-logging-limits.md
  reason: module doc required by frob:doc directive
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: points
  old_value: null
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: null
  new_value: 0.534.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
evidence:
- tests/unit/test_websec_logging_limits.py::test_websec_logging_limits_findings_fixture[websec326_positive-WEBSEC326-True]
- tests/unit/test_websec_logging_limits.py::test_websec_logging_limits_findings_fixture[websec326_negative-WEBSEC326-False]
- tests/unit/test_websec_logging_limits.py::test_websec_logging_limits_findings_fixture[websec327_positive-WEBSEC327-True]
- tests/unit/test_websec_logging_limits.py::test_websec_logging_limits_findings_fixture[websec327_negative-WEBSEC327-False]
- tests/unit/test_websec_logging_limits.py::test_websec_logging_limits_findings_fixture[websec328_positive-WEBSEC328-True]
- tests/unit/test_websec_logging_limits.py::test_websec_logging_limits_findings_fixture[websec328_negative-WEBSEC328-False]
- tests/unit/test_websec_logging_limits.py::test_websec_logging_limits_findings_fixture[websec329_positive-WEBSEC329-True]
- tests/unit/test_websec_logging_limits.py::test_websec_logging_limits_findings_fixture[websec329_negative-WEBSEC329-False]
- tests/unit/test_websec_logging_limits.py::test_websec_logging_limits_findings_fixture[websec330_positive-WEBSEC330-True]
- tests/unit/test_websec_logging_limits.py::test_websec_logging_limits_findings_fixture[websec330_negative-WEBSEC330-False]
- tests/unit/test_websec_logging_limits.py::test_websec_logging_limits_findings_fixture[websec331_positive-WEBSEC331-True]
- tests/unit/test_websec_logging_limits.py::test_websec_logging_limits_findings_fixture[websec331_negative-WEBSEC331-False]
- tests/unit/test_websec_logging_limits.py::test_websec_logging_limits_findings_fixture[websec332_positive-WEBSEC332-True]
- tests/unit/test_websec_logging_limits.py::test_websec_logging_limits_findings_fixture[websec332_negative-WEBSEC332-False]
- tests/unit/test_websec_logging_limits.py::test_websec_logging_limits_findings_fixture[websec333_positive-WEBSEC333-True]
- tests/unit/test_websec_logging_limits.py::test_websec_logging_limits_findings_fixture[websec333_negative-WEBSEC333-False]
- tests/unit/test_websec_logging_limits.py::test_websec_logging_limits_findings_fixture[websec334_positive-WEBSEC334-True]
- tests/unit/test_websec_logging_limits.py::test_websec_logging_limits_findings_fixture[websec334_negative-WEBSEC334-False]
- tests/unit/test_websec_logging_limits.py::test_websec_logging_limits_findings_no_framework_short_circuits
- tests/unit/test_websec_logging_limits.py::test_websec_findings_hook_emits_gate_violation
- tests/unit/test_websec_logging_limits.py::test_websec_findings_hook_empty_frameworks_short_circuits
- tests/unit/test_websec_logging_limits.py::test_taint_gate_discovers_websec_logging_limits_hook
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Auth-event audit logging (V16.3.1/V16.3.2), log metadata completeness + UTC timestamps, PII in logs (extends 5143-3's secret-pattern reuse with a PII field-name denylist), log-retention policy (config), outbound HTTP client timeout missing, request body size limit missing, server request timeout (config), GraphQL introspection/depth limit (config), least-functionality (debug/test routes in prod route table), outbound egress allowlist (config), client storage cleared on logout. WebSocket origin check is owned by T-5141-4, NOT this leaf -- cross-reference its rule id instead of reimplementing. Fixture per rule id.