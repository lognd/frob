---
id: T-5371
title: 'WEBPERF101-108: Core Web Vitals causes in markup'
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
- src/frob/webapp/_webperf_markup.py
- tests/fixtures/webapp/webperf1xx/markup/**
- tests/unit/test_webapp_webperf_markup.py
- docs/modules/webapp-webperf-markup.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/fixtures/webapp/webperf1xx/**
  reason: narrow shared webperf1xx fixture glob to markup-only subtree per sibling
    T-5366 split (server/**); add test+doc files for the new module
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/fixtures/webapp/webperf1xx/markup/**
  reason: narrow shared webperf1xx fixture glob to markup-only subtree per sibling
    T-5366 split (server/**); add test+doc files for the new module
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/unit/test_webapp_webperf_markup.py
  reason: narrow shared webperf1xx fixture glob to markup-only subtree per sibling
    T-5366 split (server/**); add test+doc files for the new module
  actor: logan
  at: '2026-09-24'
- op: add
  glob: docs/modules/webapp-webperf-markup.md
  reason: narrow shared webperf1xx fixture glob to markup-only subtree per sibling
    T-5366 split (server/**); add test+doc files for the new module
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: points
  old_value: null
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
Image width/height for CLS, loading=lazy on offscreen img/iframe, srcset, font-display, defer/async on head scripts, bundle-budget config assertion (webpack/vite), source-maps-in-prod cross-refs T-5143-3, not duplicated. Tree-sitter query over HTML/JSX (5147-1 substrate). Fixture per rule id.