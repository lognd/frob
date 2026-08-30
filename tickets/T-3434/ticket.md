---
id: T-3434
title: 'test_coverage_sigterm.py: signal.SIGKILL does not exist on win32'
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
- tests/system/test_coverage_sigterm.py
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
found while working T-3275 (unrelated ticket): ty flags tests/system/test_coverage_sigterm.py:177:49 unresolved-attribute [platform=win32] Module signal has no member SIGKILL. This file (landed by T-3420) already guards os.killpg via getattr for the win32 platform check but still references signal.SIGKILL directly, which genuinely does not exist on Windows (unlike SIGTERM, which does). The whole test class is already skipif(win32)'d at runtime, but ty's cross-platform static check still flags the reference. Fix the same way _send_signal_to_group's os.killpg reference was guarded (getattr(signal, 'SIGKILL', ...) or move the constant behind the same POSIX-only guard), or restructure so ty does not evaluate the win32 branch for this symbol.

## Failure log
- 2026-08-29 attempt 1: already resolved on main by T-3431: signal.SIGKILL at tests/system/test_coverage_sigterm.py is now routed through a getattr guard (_SIGKILL: int = getattr(signal, 'SIGKILL', signal.SIGTERM)), the exact fix this ticket describes. frob check --only ty shows 0 unresolved-attribute findings against this file
