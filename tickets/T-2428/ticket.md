---
id: T-2428
title: 'T-2390 child: validate [[refs.entrypoint]] against a declared schema (58 leaves,
  largest table)'
state: done
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
- src/frob/gates/_refs_schema.py
- src/frob/gates/__init__.py
- src/frob/gates/_waive.py
- src/frob/check/__init__.py
- frob.toml
- docs/modules/gates.md
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
- op: add
  glob: src/frob/gates/_refs_schema.py
  reason: 'the actual implementation touches these files: new gate module, registration
    in gates/__init__.py, rule registration, stage-group wiring, self-declaration,
    docs'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'the actual implementation touches these files: new gate module, registration
    in gates/__init__.py, rule registration, stage-group wiring, self-declaration,
    docs'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/gates/_waive.py
  reason: 'the actual implementation touches these files: new gate module, registration
    in gates/__init__.py, rule registration, stage-group wiring, self-declaration,
    docs'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/check/__init__.py
  reason: 'the actual implementation touches these files: new gate module, registration
    in gates/__init__.py, rule registration, stage-group wiring, self-declaration,
    docs'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: frob.toml
  reason: 'the actual implementation touches these files: new gate module, registration
    in gates/__init__.py, rule registration, stage-group wiring, self-declaration,
    docs'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/gates.md
  reason: 'the actual implementation touches these files: new gate module, registration
    in gates/__init__.py, rule registration, stage-group wiring, self-declaration,
    docs'
  actor: logan
  at: '2026-08-18'
evidence:
- tests/unit/test_refs_schema.py::TestRefsSchemaGate::test_must_now_fire_reports_the_undeclared_key
- tests/unit/test_refs_schema.py::TestRefsSchemaGate::test_must_still_pass_this_repos_own_frob_toml
- tests/unit/test_refs_schema.py::TestRefsSchemaGate::test_no_schema_declared_is_unresolved_not_empty
- tests/unit/test_refs_schema.py::TestRefsSchemaGate::test_unresolvable_schema_dotted_path_is_unresolved
- tests/unit/test_refs_schema.py::TestRefsSchemaGate::test_non_set_non_callable_schema_value_is_unresolved
- tests/unit/test_refs_schema.py::TestRefsSchemaGate::test_no_frob_toml_is_unresolved
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