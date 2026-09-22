---
id: T-5238
title: frob ops natives missing --path flag its flat twin frob natives has (CLI group
  parity)
state: dropped
kind: bug
origin: human
created: '2026-09-21'
priority: medium
blocked_by:
- T-4690
parent: null
tier: ticket
sprint: null
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
- tests/unit/test_cli_group_parity.py
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
Found while burning down fresh CI run 35654510898, re-verified on current dev tip. tests/unit/test_cli_group_parity.py::TestOpsGroupParity::test_every_ops_leaf_matches_its_flat_twin[natives] fails: 'frob ops natives' vs 'frob natives' option strings differ -- the flat twin has {--help, --path, -h}, the grouped ops twin only has {--help, -h}. A --path flag was added to one CLI entry point's parser without mirroring it on the other. Fix: add --path to whichever parser is missing it (likely the ops-group subcommand wiring in src/frob/app/_cli_parsers/).

## Drop reason
- 2026-09-22: duplicate of T-5205 (ops natives --path parity) (absorbed by T-5205)
