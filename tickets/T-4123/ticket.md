---
id: T-4123
title: 'SCOPE002 doc-closure debt: whole-file scope on the large ticket_runner modules
  leaves dozens of pre-existing symbols undeclared'
state: queued
kind: docs
origin: human
created: '2026-09-06'
priority: medium
blocked_by:
- T-4127
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.536.0
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
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/app/ticket_runner/_verify.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.536.0
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
Found while working T-4105: declaring the full _close_cmd.py/_land_cmd.py/_verify.py/_rapid_sweep.py files in a ticket's scope (as T-4105's own scope does) surfaces ~58 pre-existing SCOPE002 findings -- symbols in those files whose frob:doc/frob:tests targets live in docs/modules not also in scope. None of these are new; they predate T-4105's diff. Filed separately since closing this doc-closure gap for every such symbol is unrelated to T-4105's own fix (forwarding --base to nested check spawns) and would badly balloon that ticket's scope. Remedy: either add the missing docs/tests paths to whichever ticket next touches these files' scope, or decide these edges are stale and remove them.