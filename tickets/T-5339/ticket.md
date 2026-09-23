---
id: T-5339
title: EXPLAIN-obligation proof gate for waived SQL performance findings
state: queued
kind: feature
origin: human
created: '2026-09-22'
priority: high
parent: T-5148
tier: ticket
sprint: v0.536.0
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
- src/frob/gates/_sql_explain_obligation.py
- tests/fixtures/sql/**
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
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
A query flagged by 5148-2's performance rules carries a frob:tests-style obligation requiring an attached EXPLAIN ANALYZE artifact before a frob:waive on that finding is accepted -- reuse the closest existing 'proof required before waiver' precedent in frob.gates (grep for frob:invariant's binding mechanism) rather than inventing a new obligation shape. Fixture: a waiver attempt with and without the attached EXPLAIN artifact.