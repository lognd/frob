---
id: T-2437
title: 'T-2390 child: validate [dup] and [graph] tables against declared schemas'
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
- src/frob/gates/_dup.py
- src/frob/excludes.py
- tests/unit/test_dup_graph_table_schema.py
- src/frob/gates/__init__.py
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
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/__init__.py
  reason: gate registration + release wiring, same pattern as prior T-2390 children
    (src/frob/gates/_waive.py deferred -- T-2441 holds a live lease on it)
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/check/__init__.py
  reason: gate registration + release wiring, same pattern as prior T-2390 children
    (src/frob/gates/_waive.py deferred -- T-2441 holds a live lease on it)
  actor: logan
  at: '2026-08-18'
- op: add
  glob: frob.toml
  reason: gate registration + release wiring, same pattern as prior T-2390 children
    (src/frob/gates/_waive.py deferred -- T-2441 holds a live lease on it)
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/gates.md
  reason: gate registration + release wiring, same pattern as prior T-2390 children
    (src/frob/gates/_waive.py deferred -- T-2441 holds a live lease on it)
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: gate registration + release wiring, same pattern as prior T-2390 children
    (src/frob/gates/_waive.py deferred -- T-2441 holds a live lease on it)
  actor: logan
  at: '2026-08-18'
- op: add
  glob: .frob-release.json
  reason: gate registration + release wiring, same pattern as prior T-2390 children
    (src/frob/gates/_waive.py deferred -- T-2441 holds a live lease on it)
  actor: logan
  at: '2026-08-18'
- op: add
  glob: CHANGELOG.md
  reason: gate registration + release wiring, same pattern as prior T-2390 children
    (src/frob/gates/_waive.py deferred -- T-2441 holds a live lease on it)
  actor: logan
  at: '2026-08-18'
- op: add
  glob: pyproject.toml
  reason: gate registration + release wiring, same pattern as prior T-2390 children
    (src/frob/gates/_waive.py deferred -- T-2441 holds a live lease on it)
  actor: logan
  at: '2026-08-18'
- op: add
  glob: uv.lock
  reason: gate registration + release wiring, same pattern as prior T-2390 children
    (src/frob/gates/_waive.py deferred -- T-2441 holds a live lease on it)
  actor: logan
  at: '2026-08-18'
body_changes:
- mode: append
  reason: 'BUG002 cannot reproduce a pre-fix state: code already landed as T-2435''s
    disclosed passenger'
  actor: logan
  at: '2026-08-18'
  old_length: 6692
  new_length: 7126
evidence:
- tests/unit/test_dup_graph_table_schema.py::TestDupGraphSchemaGate::test_dup_must_now_fire_reports_the_undeclared_key
- tests/unit/test_dup_graph_table_schema.py::TestDupGraphSchemaGate::test_dup_must_still_pass_this_repos_own_frob_toml
- tests/unit/test_dup_graph_table_schema.py::TestDupGraphSchemaGate::test_dup_no_schema_declared_is_unresolved_not_empty
- tests/unit/test_dup_graph_table_schema.py::TestDupGraphSchemaGate::test_dup_no_frob_toml_is_unresolved
- tests/unit/test_dup_graph_table_schema.py::TestDupGraphSchemaGate::test_graph_must_now_fire_reports_the_undeclared_key
- tests/unit/test_dup_graph_table_schema.py::TestDupGraphSchemaGate::test_graph_must_still_pass_this_repos_own_frob_toml
- tests/unit/test_dup_graph_table_schema.py::TestDupGraphSchemaGate::test_graph_no_schema_declared_is_unresolved_not_empty
- tests/unit/test_dup_graph_table_schema.py::TestDupGraphSchemaGate::test_graph_no_frob_toml_is_unresolved
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Validate the `[dup]` (frob.gates._dup._dup_config) and `[graph]`
(frob.excludes, `[graph] exclude`) tables against a declared schema.
Combined into one child (unlike this epic's other children, one table
each) because both tables currently carry only 1 leaf value in this
repo's own frob.toml -- two genuinely disjoint readers, but each too
small on its own to justify a separate ticket; keep the two schema
declarations and their fixtures clearly separated in the diff (two
distinct sections, not one merged check) so a future split-out is
mechanical if either table grows.

Same required shape as every T-2390 child: module:symbol declared
schema, must-now-fire + must-still-pass fixtures per table,
Severity.UNRESOLVED (never silent) when no schema is declared, portable.

Part of T-2390's epic decomposition -- see T-2390's body for the full
disjoint-readers finding and sibling children.