---
id: T-draft-33674b0d
title: 'T-2390 child: validate top-level scalar keys (min_frob_version, check_base)
  against a declared schema'
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
- src/frob/app/_config_meta.py
- tests/unit/test_toplevel_scalar_schema.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Validate the two top-level SCALAR keys (min_frob_version, check_base --
no enclosing table at all) against a declared schema. Readers:
frob.app._config_meta / frob.app.config. Structurally different from
every other T-2390 child (no [table] to iterate, no array-of-records) --
the schema declaration here names a flat set of top-level scalar key
names rather than a table's own leaf keys; do not force this into the
same per-table shape the other children use if it does not fit, per the
epic's own "if it doesn't fit, tell the coordinator" guidance -- this is
small enough that ANY reasonable shape is fine, just keep it consistent
with the module:symbol resolver idiom the rest of the epic uses.

Part of T-2390's epic decomposition -- see T-2390's body for the full
disjoint-readers finding and sibling children.
