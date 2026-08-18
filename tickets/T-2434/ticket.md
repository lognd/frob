---
id: T-2434
title: 'T-2390 child: validate [[docblocks.commands]] table against a declared schema
  (incl. T-2397''s config=/forwarded= keys)'
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
- src/frob/gates/_docblocks_refs.py
- tests/unit/test_docblocks_table_schema.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Validate `[[docblocks.commands]]` (4 leaves in this repo currently) --
prog/parser, PLUS T-2397's own new config=/forwarded= keys (landed on
main; this child must treat those two as legitimate schema members, not
flag them as unknown). Reader: frob.gates._docblocks_refs.
_console_command_sources.

Same required shape as every T-2390 child: module:symbol declared
schema, must-now-fire + must-still-pass fixtures, Severity.UNRESOLVED
(never silent) when no schema is declared, portable.

Part of T-2390's epic decomposition -- see T-2390's body for the full
disjoint-readers finding and sibling children.
