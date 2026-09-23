---
id: T-draft-7961b103
title: 'WEBPERF109-115: server/network performance config'
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
- src/frob/webapp/_webperf_server.py
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
Compression middleware config, server cache layer for repeated expensive queries, undebounced-input-handler/unbounded-re-render React lint (hook dependency-array absence, onChange with no debounce). Cache-Control-on-hashed-assets is owned by T-5143-2, pagination-on-list-endpoints is owned by T-5144-2, and DB-pool-config is owned by T-5148-4 -- this leaf blocks on all three instead of reimplementing any of them. Fixture per rule id.