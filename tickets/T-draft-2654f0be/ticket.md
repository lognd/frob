---
id: T-draft-2654f0be
title: 'T-2390 child: validate [[refs.entrypoint]] against a declared schema (58 leaves,
  largest table)'
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
- src/frob/gates/_refs.py
- tests/unit/test_refs_schema.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: narrow the broad glob to the new test file this child will actually create
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/test_refs_schema.py
  reason: narrow the broad glob to the new test file this child will actually create
  actor: logan
  at: '2026-08-18'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Validate `[[refs.entrypoint]]` (58 leaves, this repo's LARGEST config
table -- filed as the epic's first/pattern-setting child per coordinator
instruction) against a declared schema: each entry must be exactly
{path: str, reason: str}, nothing else. Reader:
frob.gates._refs._load_allowlist (src/frob/gates/_refs.py).

REQUIRED SHAPE: reuse the module:symbol schema-declaration idiom T-2397
landed (frob.gates._docblocks_shared.resolve_dotted_symbol) -- declare
the known-key set for [[refs.entrypoint]] entries via a dotted path in
frob.toml, resolved at check time, never hardcoded to this repo's own
layout (T-2384's portability doctrine).

Fixtures required: a must-now-fire case (an entry with a plausibly
misspelled key, e.g. "paths" instead of "path", or an extra unknown key
alongside valid path/reason -- must be reported) AND a must-still-pass
control (this repo's own frob.toml, all 29 [[refs.entrypoint]] entries,
zero findings). If the control fails, report the genuinely undeclared
keys rather than weakening the check.

FAIL-LOUDLY (T-2391's doctrine, via Severity.UNRESOLVED per T-2397's own
precedent): no config surface declared at all is UNRESOLVED, never a
silent pass.

Part of T-2390's epic decomposition -- see T-2390's body for the full
disjoint-readers finding and sibling children.
