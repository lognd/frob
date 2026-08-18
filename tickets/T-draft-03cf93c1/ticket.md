---
id: T-draft-03cf93c1
title: 'T-2390 child: validate [[native]] table against a declared schema'
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
- src/frob/natives/__init__.py
- tests/unit/test_native_table_schema.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Validate `[[native]]` (6 leaves) against a declared schema: each array
entry's known keys (crate path, cargo_target_dir-shaped options, etc --
inventory the exact key set as this child's own first step). Consumers:
frob.natives, frob._cli_parsers._misc, frob.app.config.

Same required shape as every T-2390 child: module:symbol declared
schema (T-2397's resolve_dotted_symbol precedent), must-now-fire +
must-still-pass fixtures, Severity.UNRESOLVED (never silent) when no
schema is declared, portable (no hardcoded frob-specific reference).

Part of T-2390's epic decomposition -- see T-2390's body for the full
disjoint-readers finding and sibling children.
