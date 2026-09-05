---
id: T-3820
title: graph cache os.replace unguarded on Windows [WinError 5] under concurrent access
  -- retry-on-PermissionError + un-skip the transient T-3781 tests
state: in-progress
kind: bug
origin: human
created: '2026-09-05'
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
- tests/unit/test_graph_cache.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/graph/cache.py
  reason: add bounded retry-on-PermissionError/OSError around os.replace publish primitive
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/unit/test_graph_cache.py
  reason: un-skip transient T-3781 tests; narrow skip to persistent-handle cases
  actor: logan
  at: '2026-09-05'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
