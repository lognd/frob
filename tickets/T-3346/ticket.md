---
id: T-3346
title: 'Residual gate errors outside T-3342/3343/3344: ARCH/SEC/LARGE/PII/WIRE/PERF/LEXCHECK/WAIVE/FLAGCOV/DEPR
  (27)'
state: done
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/conftest.py
- src/frob/gates/_tdd_order.py
- src/frob/app/_config_external.py
- tickets/T-3385/**
scope_breadth_ack: true
scope_breadth_ack_reason: measurement-first triage ticket, no source scope yet; will
  file/scope targeted sub-tickets per root cause found (same pattern as T-3343)
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tickets/**/ticket.md
  reason: placeholder scope; will scope to actual files after triage measurement
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/conftest.py
  reason: 'T-3346 residual-gate triage: WIRE002 follow_up fix + FLAGCOV001 _BOOL_FLAGS
    fix'
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/gates/_tdd_order.py
  reason: 'T-3346 residual-gate triage: WIRE002 follow_up fix + FLAGCOV001 _BOOL_FLAGS
    fix'
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/app/_config_external.py
  reason: 'T-3346 residual-gate triage: WIRE002 follow_up fix + FLAGCOV001 _BOOL_FLAGS
    fix'
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tickets/T-3385/**
  reason: abandoned draft from a timed-out ticket-new call, dropped under T-3346;
    its own ledger write needs to be in scope
  actor: logan
  at: '2026-08-29'
evidence:
- tests/unit/test_app_config_flag_coverage.py::TestFindDroppedCliFlags::test_current_tree_has_zero_dropped_flags
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Series ED CI-gate baseline (main SHA be9e767): unscoped frob check gate-summary=188 errors. T-3342 (DOC 50), T-3343 (COV/TICK/REL/REG/REF 58), T-3344 (DRIFT 53) cover 161/188. This ticket tracks the remaining 27: gate:ARCH 3, gate:SEC 6, gate:LARGE 5, gate:PII 4, gate:WIRE 2, gate:PERF 2, gate:LEXCHECK 2, gate:WAIVE 1, gate:FLAGCOV 1, gate:DEPR 1. Small, scattered, no single root cause found yet -- needs its own per-rule triage pass. Not scoped to source files pending that triage.