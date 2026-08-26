---
id: T-2907
title: 'Strata redesign: derive the code/may tables, declare only intent, make every
  strata break an error'
state: dropped
kind: feature
origin: human
created: '2026-08-25'
priority: high
parent: null
tier: epic
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: tier
  old_value: ticket
  new_value: epic
  reason: 'T-2907 strata redesign: bootstrap and progress-surface are children of
    the derive-not-declare program'
  actor: logan
  at: '2026-08-25'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Drop reason
- 2026-08-25: user corrected the premise: auto-deriving may=/code= makes the ceiling equal whatever the code does, defeating the shrink-the-interface purpose; superseded by the shrink-only ratchet design (absorbed by T-2920)
