---
id: T-draft-44e1bb9b
title: 'T-2390 child: validate [testing] table against a declared schema (already
  has TestPolicy model)'
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
- src/frob/gates/_sys.py
- tests/unit/test_testing_table_schema.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Validate the `[testing]` table (5 leaves) against a declared schema.
NOTE (worth doing early): `TestPolicy` (frob.gates._models) is ALREADY a
real pydantic BaseModel for this table -- unlike every other T-2390
child, this one gets to test whether the schema-declaration idiom
generalizes cleanly to an ALREADY-modeled table (declare the schema as
`TestPolicy` itself, verify extra="forbid"-shaped validation actually
works once the raw table IS constructed into the model, which today it
still is not -- confirm whether [testing]'s own reader in frob.gates.
_sys constructs TestPolicy from the raw table or hand-copies fields the
same way every other T-2390 sibling does).

Same required shape as every T-2390 child: must-now-fire + must-still-
pass fixtures, Severity.UNRESOLVED (never silent) when no schema is
declared, portable (no hardcoded frob-specific reference).

Part of T-2390's epic decomposition -- see T-2390's body for the full
disjoint-readers finding and sibling children.
