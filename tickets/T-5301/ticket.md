---
id: T-5301
title: Gate rule-id registration and severity wiring for WEBSEC/COMPLY/A11Y/SEO/WEBPERF/SQL
state: queued
kind: feature
origin: human
created: '2026-09-22'
priority: high
parent: T-5140
tier: ticket
sprint: v0.535.0
runs_last: false
milestone: null
points: 2
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_waive.py
- frob.toml
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '2'
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '2'
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '2'
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '2'
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '2'
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Add all WEBSEC/COMPLY/A11Y/SEO/WEBPERF/SQL rule-id ranges to _KNOWN_GATE_RULES as a reserved block (placeholder comments naming the future ticket, same shape as PERF015-018's T-5136 reservation) so frob:waive on an unshipped rule id fails loud, not silently. Add a [gates.severity] block: WEBSEC/COMPLY/A11Y default error; SEO/WEBPERF default warn until a repo opts to promote (PERF015-018 precedent). LAUNCH severity is handled separately by WEBSUB-4 (new advisory tier), not this leaf. Positive-control: frob:waive WEBSEC101 reason=... round-trips through known-rule-id checks without raising UnknownRuleId once this leaf lands. Doc: docs/modules/gates.md's rule table (skeleton rows).