---
id: T-5474
title: 'cli_group_parity: frob ops natives missing --path option present on flat twin'
state: queued
kind: bug
origin: agent
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
Found while draining CI run 35951365410 (dev 9e0c89bb19). Failing:
tests/unit/test_cli_group_parity.py::TestOpsGroupParity::test_every_ops_leaf_matches_its_flat_twin[natives]

The grouped CLI surface (frob ops natives) and its flat twin (frob
natives) have diverged: {'--help', '-h'} vs {'--help', '--path', '-h'} --
the flat twin has a --path option the grouped twin is missing.

Fix: add the missing --path option to the grouped (frob ops natives) CLI
definition so both surfaces match again -- contained CLI-wiring fix, in
touch-scope.
