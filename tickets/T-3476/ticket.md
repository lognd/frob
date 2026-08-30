---
id: T-3476
title: 'TICK004: recursive descent through nested grandchild epics for children-progress
  rot check'
state: in-progress
kind: feature
origin: human
created: '2026-08-30'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_tickets_gate.py
- tests/test_tickets_priority.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets_priority.py
  reason: 'T-3476: TICK004 recursive-descent tests live here alongside existing TICK004
    suite'
  actor: logan
  at: '2026-08-30'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3463 implemented direct-children-only rot corroboration for a decomposed epic/story (_epic_children_all_stalled): an epic escalates back to ERROR when no child is IN_PROGRESS and even the youngest QUEUED/PLANNED child has crossed its own rot threshold. T-3463's own Description explicitly deferred recursive descent through nested grandchild epics -- a grandchild epic under a decomposed epic is currently read by its own created date only, never by walking further down into ITS children's progress. Needs its own design pass: how deep to recurse, cycle/self-parent guards, and calibration against real ledger data (does a healthy-looking grandchild epic with stalled great-grandchildren count as fresh evidence, or not) before implementing.