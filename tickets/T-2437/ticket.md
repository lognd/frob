---
id: T-2437
title: 'T-2390 child: validate [dup] and [graph] tables against declared schemas'
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: high
parent: T-2390
tier: story
sprint: null
runs_last: false
scope:
- src/frob/gates/_dup.py
- src/frob/excludes.py
- tests/unit/test_dup_graph_table_schema.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Validate the `[dup]` (frob.gates._dup._dup_config) and `[graph]`
(frob.excludes, `[graph] exclude`) tables against a declared schema.
Combined into one child (unlike this epic's other children, one table
each) because both tables currently carry only 1 leaf value in this
repo's own frob.toml -- two genuinely disjoint readers, but each too
small on its own to justify a separate ticket; keep the two schema
declarations and their fixtures clearly separated in the diff (two
distinct sections, not one merged check) so a future split-out is
mechanical if either table grows.

Same required shape as every T-2390 child: module:symbol declared
schema, must-now-fire + must-still-pass fixtures per table,
Severity.UNRESOLVED (never silent) when no schema is declared, portable.

Part of T-2390's epic decomposition -- see T-2390's body for the full
disjoint-readers finding and sibling children.
