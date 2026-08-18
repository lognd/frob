---
id: T-2433
title: 'T-2390 child: validate [arch] table against a declared schema'
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
- tests/unit/test_arch_table_schema.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Validate the `[arch]` table (9 leaves) against a declared schema.
Reader: frob.app._config_meta.load_arch_config -- hand-lists 10 named
keys (5 T-0373 thresholds + 5 T-0728 SRP/cohesion knobs) against its own
calibrated-defaults dict; a misspelled key (e.g. "max_fuction_lines",
this epic's own filing-time example) silently reverts to the built-in
default with no diagnostic.

Same required shape as every T-2390 child: module:symbol declared
schema (T-2397's resolve_dotted_symbol precedent), must-now-fire +
must-still-pass fixtures, Severity.UNRESOLVED (never silent) when no
schema is declared, portable (no hardcoded frob-specific reference).

Part of T-2390's epic decomposition -- see T-2390's body for the full
disjoint-readers finding and sibling children.
