---
id: T-5205
title: 'frob ops natives vs flat frob natives: --path option divergence (test_cli_group_parity
  pre-existing failure)'
state: queued
kind: bug
origin: human
created: '2026-09-21'
priority: medium
parent: null
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/_cli_parsers/_ops.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-4690: tests/unit/test_cli_group_parity.py::TestOpsGroupParity::test_every_ops_leaf_matches_its_flat_twin[natives] fails on dev (confirmed pre-existing, unrelated to T-4690 -- _ops.py's natives leaf was not touched by that ticket). 'frob ops natives' has only {-h,--help}; flat 'frob natives' additionally has --path. One of the two parsers is missing a flag the other has; needs investigation and a fix to restore parity.