---
id: T-3351
title: Fix frob:tests Class::method separator in check_runner.py (2 DRIFT002 findings)
state: queued
kind: bug
origin: human
created: '2026-08-29'
priority: medium
blocked_by:
- T-3326
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 1.0.0
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
- src/frob/app/check_runner.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: v0.532.0
  new_value: backlog
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-15'
- field: milestone
  old_value: v0.532.0
  new_value: 1.0.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-15'
- field: sprint
  old_value: backlog
  new_value: v0.540.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Deferred from T-3344 (gate:DRIFT burn-down) because T-3326 holds an in-progress lease on this file and landing would create CrossTicketLeakage. Same fix as T-3344's other 12 files: two frob:tests directives at lines ~351/354 use TestTaskProgressCallback::test_... (double-colon) instead of the graph's TestTaskProgressCallback.test_... (dot) qualname convention, so DRIFT002 flags them as unresolvable. Apply once T-3326 closes.