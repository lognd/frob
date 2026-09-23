---
id: T-5370
title: 'COMPLY117-122: sector-specific (HIPAA/GLBA/COPPA/FERPA, flag-gated)'
state: queued
kind: feature
origin: human
created: '2026-09-23'
priority: high
parent: T-5145
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
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
- src/frob/webapp/_comply_sector.py
- tests/fixtures/webapp/comply1xx/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
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
---
All applicability-flag-gated per the corpus (financial_institution=true, directed_to_children=true) -- ship as config-driven rules reading a [comply] table in frob.toml the repo opts into, never inferred. Fixture: frob.toml fixture with each flag set.