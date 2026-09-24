---
id: T-3010
title: 'Incremental releases: milestone-scoped closure over a configuration binding
  partial architectures with declared gaps (T-3004 section 6)'
state: queued
kind: feature
origin: human
created: '2026-08-26'
priority: high
parent: T-3004
tier: ticket
sprint: strata-vmodel
runs_last: false
milestone: 0.535.0
points: 8
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- strata-core/src/graph/vmodel/closure.rs
- src/frob/gates/_strata_milestone_closure.py
- tests/unit/strata/test_vmodel_check.py
- tests/gates/test_milestone_closure.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: strata-core/src/graph/vmodel/closure.rs
  reason: milestone-scoped closure over configuration binding
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/gates/_strata_milestone_closure.py
  reason: milestone-scoped closure over configuration binding
  actor: logan
  at: '2026-09-23'
- op: add
  glob: tests/unit/strata/test_vmodel_check.py
  reason: milestone-scoped closure over configuration binding
  actor: logan
  at: '2026-09-23'
- op: add
  glob: tests/gates/test_milestone_closure.py
  reason: milestone-scoped closure over configuration binding
  actor: logan
  at: '2026-09-23'
triage_changes:
- field: parent
  old_value: null
  new_value: T-3004
  reason: T-3004 decomposition per the owner design decision
  actor: logan
  at: '2026-08-26'
- field: milestone
  old_value: 1.1.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-23'
- field: sprint
  old_value: null
  new_value: strata-vmodel
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: null
  new_value: '8'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
