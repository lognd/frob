---
id: T-6479
title: 'SYSDESIGN408: (pool_size_per_replica * max_replicas) exceeds declared DB max_connections'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-6460
parent: T-6410
tier: ticket
sprint: sysdesign
runs_last: false
milestone: 0.539.0
points: null
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
- src/frob/sysdesign/_horizontal.py
- tests/fixtures/sysdesign/sysdesign408/**
scope_breadth_ack: true
scope_breadth_ack_reason: sysdesign epic tree, scope reviewed by coordinator
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: SYSDESIGN409: (pool_size_per_replica * max_replicas) exceeds declared DB max_connections
kind: feature
tier: leaf
parent: T-SYS-SF
milestone: 0.539.0
sprint: sysdesign
points: 3
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/sysdesign/_horizontal.py, docs/modules/gates.md (SYSDESIGN409 row),
       tests/fixtures/sysdesign/sysdesign409/**
blocked_by: [T-SYS-A-INFRA-STORE]
tag: Static: design

Research row 7.9 (not independently sourced with a direct "pool size x replicas <= max
connections" quote this pass; AWS REL05-BP06 stateless/offload guidance cited contextually).
Lint condition: "(pool_size_per_replica * max_replicas) > declared DB max_connections flags a
scale-out-triggered connection exhaustion risk."

Acceptance criteria: reads the app's DB-client pool-size config, the design model's
`capacity replicas N..M`, and the target store's declared connection limit (or a
config-declared `max_connections`); flags when the arithmetic product exceeds the limit.
Positive-control fixture: tests/fixtures/sysdesign/sysdesign409/pool-times-replicas-exceeds-
max-connections/**.
