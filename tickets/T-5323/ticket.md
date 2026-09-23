---
id: T-5323
title: 'A11Y101-115: non-text content, structure, forms'
state: queued
kind: feature
origin: human
created: '2026-09-22'
priority: high
blocked_by:
- T-5313
parent: T-5146
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
scope:
- src/frob/webapp/_a11y_structure.py
- tests/fixtures/webapp/a11y1xx/structure/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/fixtures/webapp/a11y1xx/**
  reason: narrow shared fixture glob to a per-leaf subdirectory so the four accessibility
    leaves can hold concurrent leases
  actor: logan
  at: '2026-09-23'
- op: add
  glob: tests/fixtures/webapp/a11y1xx/structure/**
  reason: narrow shared fixture glob to a per-leaf subdirectory so the four accessibility
    leaves can hold concurrent leases
  actor: logan
  at: '2026-09-23'
triage_changes:
- field: points
  old_value: null
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '5'
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
  at: '2026-09-23'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
alt on img/svg role=img (SC 1.1.1), heading order + single h1 (SC 1.3.1), page title present/non-empty (SC 2.4.2), html lang (SC 3.1.1), link/button accessible names (SC 2.4.4, no generic 'click here'), form-input label association, autocomplete on identity fields (SC 1.3.5), duplicate ids, invalid ARIA role/attribute pairs. Fixture per rule id via 5146-1's query helpers.