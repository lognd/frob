---
id: T-2936
title: 'frob does not IMPORT on Windows: signal.SIGKILL evaluated as a default arg
  at module load crashes in 54s before any test runs'
state: queued
kind: bug
origin: human
created: '2026-08-26'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/process/_reap.py
- docs/modules/process.md
- src/frob/gates/__init__.py
- tests/unit/test_process_reap.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/process/_reap.py
  reason: fix signal.SIGKILL default-arg evaluated at import time
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/process.md
  reason: doc anchors for touched symbols
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/gates/__init__.py
  reason: remove now-unnecessary explicit signal.SIGKILL call-site arg, defer to the
    safe internal default
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/unit/test_process_reap.py
  reason: update fixtures + add must-fire/must-stay-quiet import-time repro tests
  actor: logan
  at: '2026-08-26'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
