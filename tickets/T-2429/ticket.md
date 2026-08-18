---
id: T-2429
title: 'T-2390 child: validate [[native]] table against a declared schema'
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
- src/frob/natives/__init__.py
- tests/unit/test_native_table_schema.py
- src/frob/gates/__init__.py
- src/frob/gates/_waive.py
- src/frob/check/__init__.py
- frob.toml
- docs/modules/gates.md
- docs/design/registry/check-coverage.yaml
- .frob-release.json
- CHANGELOG.md
- pyproject.toml
- uv.lock
- src/frob/gates/_native_schema.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/natives/_native_schema.py
  reason: add wiring files for REFSCHEMA idiom gate registration, same pattern as
    T-2428
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/gates/__init__.py
  reason: add wiring files for REFSCHEMA idiom gate registration, same pattern as
    T-2428
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/gates/_waive.py
  reason: add wiring files for REFSCHEMA idiom gate registration, same pattern as
    T-2428
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/check/__init__.py
  reason: add wiring files for REFSCHEMA idiom gate registration, same pattern as
    T-2428
  actor: logan
  at: '2026-08-18'
- op: add
  glob: frob.toml
  reason: add wiring files for REFSCHEMA idiom gate registration, same pattern as
    T-2428
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/gates.md
  reason: add wiring files for REFSCHEMA idiom gate registration, same pattern as
    T-2428
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: gate registry needs the new rule entry, same as T-2428
  actor: logan
  at: '2026-08-18'
- op: add
  glob: .frob-release.json
  reason: release stamp/sync mechanically touches these, same as every other T-2390
    child land
  actor: logan
  at: '2026-08-18'
- op: add
  glob: CHANGELOG.md
  reason: release stamp/sync mechanically touches these, same as every other T-2390
    child land
  actor: logan
  at: '2026-08-18'
- op: add
  glob: pyproject.toml
  reason: release stamp/sync mechanically touches these, same as every other T-2390
    child land
  actor: logan
  at: '2026-08-18'
- op: add
  glob: uv.lock
  reason: release stamp/sync mechanically touches these, same as every other T-2390
    child land
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: src/frob/natives/_native_schema.py
  reason: moved schema module into gates/ to avoid a cross-component gates<->natives
    Flow that a natives-package location would require declaring in design/frob.strata
    (out of this child's scope), following T-2428's own gates/-resident schema module
    pattern
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/gates/_native_schema.py
  reason: moved schema module into gates/ to avoid a cross-component gates<->natives
    Flow that a natives-package location would require declaring in design/frob.strata
    (out of this child's scope), following T-2428's own gates/-resident schema module
    pattern
  actor: logan
  at: '2026-08-18'
evidence:
- tests/unit/test_native_table_schema.py::TestNativeSchemaGate::test_must_now_fire_reports_the_undeclared_key
- tests/unit/test_native_table_schema.py::TestNativeSchemaGate::test_must_still_pass_this_repos_own_frob_toml
- tests/unit/test_native_table_schema.py::TestNativeSchemaGate::test_no_schema_declared_is_unresolved_not_empty
- tests/unit/test_native_table_schema.py::TestNativeSchemaGate::test_unresolvable_schema_dotted_path_is_unresolved
- tests/unit/test_native_table_schema.py::TestNativeSchemaGate::test_non_set_non_callable_schema_value_is_unresolved
- tests/unit/test_native_table_schema.py::TestNativeSchemaGate::test_no_frob_toml_is_unresolved
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 2be5ff72a44dd3aa4dcba20d8c577f580ab460e6
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