---
id: T-5371
title: 'WEBPERF101-108: Core Web Vitals causes in markup'
state: queued
kind: feature
origin: human
created: '2026-09-23'
priority: high
parent: T-5147
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/webapp/_webperf_markup.py
- tests/fixtures/webapp/webperf1xx/**
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
Image width/height for CLS, loading=lazy on offscreen img/iframe, srcset, font-display, defer/async on head scripts, bundle-budget config assertion (webpack/vite), source-maps-in-prod cross-refs T-5143-3, not duplicated. Tree-sitter query over HTML/JSX (5147-1 substrate). Fixture per rule id.