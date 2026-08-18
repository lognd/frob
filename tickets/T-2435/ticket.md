---
id: T-2435
title: 'T-2390 child: validate [gates] table (incl. [gates.ratchet]) against a declared
  schema'
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
- src/frob/gates/_ratchet.py
- tests/unit/test_gates_table_schema.py
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
evidence:
- tests/unit/test_gates_table_schema.py::TestGatesSchemaGate::test_must_now_fire_reports_the_undeclared_ratchet_key
- tests/unit/test_gates_table_schema.py::TestGatesSchemaGate::test_must_now_fire_reports_the_unregistered_severity_rule_id
- tests/unit/test_gates_table_schema.py::TestGatesSchemaGate::test_must_still_pass_this_repos_own_frob_toml
- tests/unit/test_gates_table_schema.py::TestGatesSchemaGate::test_no_ratchet_schema_declared_is_unresolved_not_empty
- tests/unit/test_gates_table_schema.py::TestGatesSchemaGate::test_unresolvable_ratchet_schema_dotted_path_is_unresolved
- tests/unit/test_gates_table_schema.py::TestGatesSchemaGate::test_no_frob_toml_is_unresolved
- tests/unit/test_gates_table_schema.py::TestGatesSchemaGate::test_no_gates_table_at_all_is_clean_not_error
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: b8cd448de7020293854b0f1fe734a7f1409ce561
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