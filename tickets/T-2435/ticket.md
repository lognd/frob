---
id: T-2435
title: 'T-2390 child: validate [gates] table (incl. [gates.ratchet]) against a declared
  schema'
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
- src/frob/gates/_ratchet.py
- tests/unit/test_gates_table_schema.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Validate the `[gates]` table (19 leaves, includes nested
`[gates.ratchet]`) against a declared schema. Readers span
frob.gates._ratchet ([gates.ratchet.rules]) and other [gates]-nested
sub-tables -- inventory the full [gates] key surface first (this was
NOT fully surveyed at T-2390 filing time; do that as this child's own
first step, do not assume the one reader named here is exhaustive).

Same required shape as every T-2390 child: module:symbol declared
schema (T-2397's resolve_dotted_symbol precedent), must-now-fire +
must-still-pass fixtures, Severity.UNRESOLVED (never silent) when no
schema is declared, portable (no hardcoded frob-specific reference).

Part of T-2390's epic decomposition -- see T-2390's body for the full
disjoint-readers finding and sibling children.
