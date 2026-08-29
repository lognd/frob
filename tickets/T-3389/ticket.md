---
id: T-3389
title: Declare SEC110 unmapped env-var reads (logger, main, frob-suggest hook, worktree_guard
  test)
state: queued
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/logging/logger.py
- src/frob/__main__.py
- .claude/hooks/frob-suggest.py
- tests/test_worktree_guard.py
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
SEC110: 6 env-var reads without declared mapping. Map each read to its purpose per gate:SEC contract. Part of PyPI release error-floor burn (Series EQ slice).