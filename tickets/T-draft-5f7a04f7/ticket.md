---
id: T-draft-5f7a04f7
title: 'frob ops natives vs flat frob natives: --path option divergence (test_cli_group_parity
  pre-existing failure)'
state: queued
kind: bug
origin: human
created: '2026-09-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/_cli_parsers/_ops.py
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
found while working T-4690: tests/unit/test_cli_group_parity.py::TestOpsGroupParity::test_every_ops_leaf_matches_its_flat_twin[natives] fails on dev (confirmed pre-existing, unrelated to T-4690 -- _ops.py's natives leaf was not touched by that ticket). 'frob ops natives' has only {-h,--help}; flat 'frob natives' additionally has --path. One of the two parsers is missing a flag the other has; needs investigation and a fix to restore parity.