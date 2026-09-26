---
id: T-6591
title: 10 bare-node-id frob:tests directives in _land.py:602-620 (same Windows stat
  bug as T-6527)
state: queued
kind: bug
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-5161
parent: T-5630
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
flavour: null
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
- src/frob/tickets/_land.py
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
Found while working T-6527. src/frob/tickets/_land.py:602-620 carries 10 frob:tests directives targeting TestLandLockWaitBudgetFromDeclaredDeadline/TestLandLockInlineWaitDefaultsNearZero methods with no path:: prefix -- the exact same bare-node-id shape T-6527 fixed at src/frob/process/_derived_lock.py:80 (str(ref).split('::', 1)[0] returns the whole bare string as a bogus 'file', which reaches a real stat()/parse call and raises WinError 2 on windows-latest during the self-gate). Fix: prefix each with tests/ticket_land_suite/test_land_lock.py::. Blocked by T-5161 which currently leases this file.