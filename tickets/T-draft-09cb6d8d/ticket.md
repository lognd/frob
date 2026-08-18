---
id: T-draft-09cb6d8d
title: 'T-2390 child: validate [profile] table against a declared schema'
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
- src/frob/tickets/_profile.py
- tests/unit/test_profile_table_schema.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Validate the `[profile]` table (2 leaves) against a declared schema.
Reader: frob.tickets._profile.

Same required shape as every T-2390 child: module:symbol declared
schema, must-now-fire + must-still-pass fixtures, Severity.UNRESOLVED
(never silent) when no schema is declared, portable. Smallest child in
this epic -- good candidate to pick up quickly once the pattern is
proven on T-2390's own first (refs) child.

Part of T-2390's epic decomposition -- see T-2390's body for the full
disjoint-readers finding and sibling children.
