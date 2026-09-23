---
id: T-5364
title: 'SEO/WEBPERF substrate: per-route head metadata extraction'
state: queued
kind: feature
origin: human
created: '2026-09-23'
priority: high
blocked_by:
- T-5302
parent: T-5147
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
- src/frob/webapp/_seo_substrate.py
- tests/fixtures/webapp/seo1xx/**
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
Tree-sitter query over HTML/JSX for <head> contents (title, meta tags, link tags, JSON-LD script blocks) normalized into a PageMetadata model per route, reused by every SEO/WEBPERF rule below instead of re-querying the DOM each time. Also builds the route-table-wide duplicate-detection index. Fixture: multi-route fixture app with one duplicate-title pair planted.