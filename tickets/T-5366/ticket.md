---
id: T-5366
title: 'WEBPERF109-115: server/network performance config'
state: queued
kind: feature
origin: human
created: '2026-09-23'
priority: high
blocked_by:
- T-5364
parent: T-5147
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
worktree: null
branch: null
scope:
- src/frob/webapp/_webperf_server.py
- tests/fixtures/webapp/webperf1xx/server/**
- tests/unit/test_webperf_server.py
- docs/modules/webapp-webperf-server.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/fixtures/webapp/webperf1xx/**
  reason: per-ticket fixture subdir (sibling T-5371 owns markup/**) plus test file
    and module doc, batched at intake
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/fixtures/webapp/webperf1xx/server/**
  reason: per-ticket fixture subdir (sibling T-5371 owns markup/**) plus test file
    and module doc, batched at intake
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/unit/test_webperf_server.py
  reason: per-ticket fixture subdir (sibling T-5371 owns markup/**) plus test file
    and module doc, batched at intake
  actor: logan
  at: '2026-09-24'
- op: add
  glob: docs/modules/webapp-webperf-server.md
  reason: per-ticket fixture subdir (sibling T-5371 owns markup/**) plus test file
    and module doc, batched at intake
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
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Compression middleware config, server cache layer for repeated expensive queries, undebounced-input-handler/unbounded-re-render React lint (hook dependency-array absence, onChange with no debounce). Cache-Control-on-hashed-assets is owned by T-5143-2, pagination-on-list-endpoints is owned by T-5144-2, and DB-pool-config is owned by T-5148-4 -- this leaf blocks on all three instead of reimplementing any of them. Fixture per rule id.