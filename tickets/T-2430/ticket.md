---
id: T-2430
title: 'T-2390 child: validate [profile] table against a declared schema'
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
- src/frob/tickets/_profile.py
- tests/unit/test_profile_table_schema.py
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/__init__.py
  reason: gate registration + release stamp wiring, same pattern as T-2428/T-2429
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/gates/_waive.py
  reason: gate registration + release stamp wiring, same pattern as T-2428/T-2429
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/check/__init__.py
  reason: gate registration + release stamp wiring, same pattern as T-2428/T-2429
  actor: logan
  at: '2026-08-18'
- op: add
  glob: frob.toml
  reason: gate registration + release stamp wiring, same pattern as T-2428/T-2429
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/gates.md
  reason: gate registration + release stamp wiring, same pattern as T-2428/T-2429
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: gate registration + release stamp wiring, same pattern as T-2428/T-2429
  actor: logan
  at: '2026-08-18'
- op: add
  glob: .frob-release.json
  reason: gate registration + release stamp wiring, same pattern as T-2428/T-2429
  actor: logan
  at: '2026-08-18'
- op: add
  glob: CHANGELOG.md
  reason: gate registration + release stamp wiring, same pattern as T-2428/T-2429
  actor: logan
  at: '2026-08-18'
- op: add
  glob: pyproject.toml
  reason: gate registration + release stamp wiring, same pattern as T-2428/T-2429
  actor: logan
  at: '2026-08-18'
- op: add
  glob: uv.lock
  reason: gate registration + release stamp wiring, same pattern as T-2428/T-2429
  actor: logan
  at: '2026-08-18'
evidence:
- tests/unit/test_profile_table_schema.py::TestProfileSchemaGate::test_must_now_fire_reports_the_undeclared_key
- tests/unit/test_profile_table_schema.py::TestProfileSchemaGate::test_must_still_pass_this_repos_own_frob_toml
- tests/unit/test_profile_table_schema.py::TestProfileSchemaGate::test_no_schema_declared_is_unresolved_not_empty
- tests/unit/test_profile_table_schema.py::TestProfileSchemaGate::test_unresolvable_schema_dotted_path_is_unresolved
- tests/unit/test_profile_table_schema.py::TestProfileSchemaGate::test_non_set_non_callable_schema_value_is_unresolved
- tests/unit/test_profile_table_schema.py::TestProfileSchemaGate::test_no_frob_toml_is_unresolved
- tests/unit/test_profile_table_schema.py::TestProfileSchemaGate::test_no_profile_table_at_all_is_clean_not_error
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