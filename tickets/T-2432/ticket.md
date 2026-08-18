---
id: T-2432
title: 'T-2390 child: validate [testing] table against a declared schema (already
  has TestPolicy model)'
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
- src/frob/gates/_sys.py
- tests/unit/test_testing_table_schema.py
- src/frob/gates/_models.py
- frob.toml
- docs/modules/gates.md
- docs/design/registry/check-coverage.yaml
- .frob-release.json
- CHANGELOG.md
- pyproject.toml
- uv.lock
- src/frob/gates/__init__.py
- src/frob/gates/_waive.py
- src/frob/check/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_models.py
  reason: TestPolicy model lives in _sys.py's own imports (_models.py); [testing]
    reader is _sys.py (already in scope); gate registration + release wiring, same
    pattern as prior T-2390 children
  actor: logan
  at: '2026-08-18'
- op: add
  glob: frob.toml
  reason: TestPolicy model lives in _sys.py's own imports (_models.py); [testing]
    reader is _sys.py (already in scope); gate registration + release wiring, same
    pattern as prior T-2390 children
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/gates.md
  reason: TestPolicy model lives in _sys.py's own imports (_models.py); [testing]
    reader is _sys.py (already in scope); gate registration + release wiring, same
    pattern as prior T-2390 children
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: TestPolicy model lives in _sys.py's own imports (_models.py); [testing]
    reader is _sys.py (already in scope); gate registration + release wiring, same
    pattern as prior T-2390 children
  actor: logan
  at: '2026-08-18'
- op: add
  glob: .frob-release.json
  reason: TestPolicy model lives in _sys.py's own imports (_models.py); [testing]
    reader is _sys.py (already in scope); gate registration + release wiring, same
    pattern as prior T-2390 children
  actor: logan
  at: '2026-08-18'
- op: add
  glob: CHANGELOG.md
  reason: TestPolicy model lives in _sys.py's own imports (_models.py); [testing]
    reader is _sys.py (already in scope); gate registration + release wiring, same
    pattern as prior T-2390 children
  actor: logan
  at: '2026-08-18'
- op: add
  glob: pyproject.toml
  reason: TestPolicy model lives in _sys.py's own imports (_models.py); [testing]
    reader is _sys.py (already in scope); gate registration + release wiring, same
    pattern as prior T-2390 children
  actor: logan
  at: '2026-08-18'
- op: add
  glob: uv.lock
  reason: TestPolicy model lives in _sys.py's own imports (_models.py); [testing]
    reader is _sys.py (already in scope); gate registration + release wiring, same
    pattern as prior T-2390 children
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/gates/__init__.py
  reason: gate wiring sites, same shape as prior T-2390 children
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/gates/_waive.py
  reason: gate wiring sites, same shape as prior T-2390 children
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/check/__init__.py
  reason: gate wiring sites, same shape as prior T-2390 children
  actor: logan
  at: '2026-08-18'
evidence:
- tests/unit/test_testing_table_schema.py::TestTestingSchemaGate::test_testing_known_keys_reads_test_policy_model_fields
- tests/unit/test_testing_table_schema.py::TestTestingSchemaGate::test_must_now_fire_reports_the_undeclared_key
- tests/unit/test_testing_table_schema.py::TestTestingSchemaGate::test_must_still_pass_this_repos_own_frob_toml
- tests/unit/test_testing_table_schema.py::TestTestingSchemaGate::test_no_schema_declared_is_unresolved_not_empty
- tests/unit/test_testing_table_schema.py::TestTestingSchemaGate::test_unresolvable_schema_dotted_path_is_unresolved
- tests/unit/test_testing_table_schema.py::TestTestingSchemaGate::test_non_set_non_callable_schema_value_is_unresolved
- tests/unit/test_testing_table_schema.py::TestTestingSchemaGate::test_no_frob_toml_is_unresolved
- tests/unit/test_testing_table_schema.py::TestTestingSchemaGate::test_no_testing_table_at_all_is_clean_not_error
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