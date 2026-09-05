---
id: T-3818
title: 'T-3797 regression: check tool-runners render Err(SpawnFailed) as tool_disabled
  instead of tool_unavailable (mac+ubuntu red on test_check_tool_unavailable)'
state: queued
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
- src/frob/check/_python.py
- src/frob/check/_native.py
- src/frob/check/_ts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/check/_python.py
  reason: fix Err(SpawnFailed) rendering at all tool-runner sites
  actor: logan
  at: '2026-09-05'
- op: add
  glob: src/frob/check/_native.py
  reason: fix Err(SpawnFailed) rendering at all tool-runner sites
  actor: logan
  at: '2026-09-05'
- op: add
  glob: src/frob/check/_ts.py
  reason: fix Err(SpawnFailed) rendering at all tool-runner sites
  actor: logan
  at: '2026-09-05'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
