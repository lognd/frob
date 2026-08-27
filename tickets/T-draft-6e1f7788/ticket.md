---
id: T-draft-6e1f7788
title: 'frob check cache.db/parse-artifacts.db: database is locked under concurrent
  checks'
state: queued
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/cache.py
- docs/modules/graph.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/_cache.py
  reason: 'correct scope: cache.connect/database-is-locked lives in graph/cache.py,
    not gates'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: src/frob/graph/cache.py
  reason: 'correct scope: cache.connect/database-is-locked lives in graph/cache.py,
    not gates'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: docs/modules/graph.md
  reason: doc anchor closure for graph/cache.py symbols
  actor: logan
  at: '2026-08-27'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
