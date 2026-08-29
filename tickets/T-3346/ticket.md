---
id: T-3346
title: 'Residual gate errors outside T-3342/3343/3344: ARCH/SEC/LARGE/PII/WIRE/PERF/LEXCHECK/WAIVE/FLAGCOV/DEPR
  (27)'
state: queued
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
- tickets/**/ticket.md
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
Series ED CI-gate baseline (main SHA be9e767): unscoped frob check gate-summary=188 errors. T-3342 (DOC 50), T-3343 (COV/TICK/REL/REG/REF 58), T-3344 (DRIFT 53) cover 161/188. This ticket tracks the remaining 27: gate:ARCH 3, gate:SEC 6, gate:LARGE 5, gate:PII 4, gate:WIRE 2, gate:PERF 2, gate:LEXCHECK 2, gate:WAIVE 1, gate:FLAGCOV 1, gate:DEPR 1. Small, scattered, no single root cause found yet -- needs its own per-rule triage pass. Not scoped to source files pending that triage.