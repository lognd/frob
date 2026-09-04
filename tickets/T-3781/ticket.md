---
id: T-3781
title: fix win32 failures in graph cache sqlite handle tests
state: queued
kind: bug
origin: human
created: '2026-09-04'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_graph_cache.py
- src/frob/graph/cache.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/graph/**
  reason: narrow away from the whole graph package to avoid overlap with T-1608/T-1609/T-3213/T-3248/T-3573
  actor: logan
  at: '2026-09-04'
- op: add
  glob: src/frob/graph/cache.py
  reason: the sqlite cache module is the actual fix surface for the win32 handle/replace
    failures
  actor: logan
  at: '2026-09-04'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Windows CI failures in tests/unit/test_graph_cache.py (6): TestConnectNeverReturnsAStaleConnection, TestHandleIdentity (3), TestRecreateConcurrentReaderSurvives, TestRecreateNeverExposesASchemaIncompleteDb. Likely sqlite file-handle/replace on Windows (Windows forbids replacing/removing an open file) needing a real fix (close handle before os.replace, or retry-on-PermissionError).