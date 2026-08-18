---
id: T-2431
title: 'T-2390 child: validate top-level scalar keys (min_frob_version, check_base)
  against a declared schema'
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
- tests/unit/test_toplevel_scalar_schema.py
- src/frob/repo_meta.py
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
- op: remove
  glob: src/frob/app/_config_meta.py
  reason: reader file renamed _config_meta.py->repo_meta.py by a prior land; plus
    gate registration + release wiring, same pattern as prior T-2390 children
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/repo_meta.py
  reason: reader file renamed _config_meta.py->repo_meta.py by a prior land; plus
    gate registration + release wiring, same pattern as prior T-2390 children
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/gates/__init__.py
  reason: reader file renamed _config_meta.py->repo_meta.py by a prior land; plus
    gate registration + release wiring, same pattern as prior T-2390 children
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/gates/_waive.py
  reason: reader file renamed _config_meta.py->repo_meta.py by a prior land; plus
    gate registration + release wiring, same pattern as prior T-2390 children
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/check/__init__.py
  reason: reader file renamed _config_meta.py->repo_meta.py by a prior land; plus
    gate registration + release wiring, same pattern as prior T-2390 children
  actor: logan
  at: '2026-08-18'
- op: add
  glob: frob.toml
  reason: reader file renamed _config_meta.py->repo_meta.py by a prior land; plus
    gate registration + release wiring, same pattern as prior T-2390 children
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/gates.md
  reason: reader file renamed _config_meta.py->repo_meta.py by a prior land; plus
    gate registration + release wiring, same pattern as prior T-2390 children
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: reader file renamed _config_meta.py->repo_meta.py by a prior land; plus
    gate registration + release wiring, same pattern as prior T-2390 children
  actor: logan
  at: '2026-08-18'
- op: add
  glob: .frob-release.json
  reason: reader file renamed _config_meta.py->repo_meta.py by a prior land; plus
    gate registration + release wiring, same pattern as prior T-2390 children
  actor: logan
  at: '2026-08-18'
- op: add
  glob: CHANGELOG.md
  reason: reader file renamed _config_meta.py->repo_meta.py by a prior land; plus
    gate registration + release wiring, same pattern as prior T-2390 children
  actor: logan
  at: '2026-08-18'
- op: add
  glob: pyproject.toml
  reason: reader file renamed _config_meta.py->repo_meta.py by a prior land; plus
    gate registration + release wiring, same pattern as prior T-2390 children
  actor: logan
  at: '2026-08-18'
- op: add
  glob: uv.lock
  reason: reader file renamed _config_meta.py->repo_meta.py by a prior land; plus
    gate registration + release wiring, same pattern as prior T-2390 children
  actor: logan
  at: '2026-08-18'
evidence:
- tests/unit/test_toplevel_scalar_schema.py::TestTopLevelScalarSchemaGate::test_must_now_fire_reports_the_undeclared_key
- tests/unit/test_toplevel_scalar_schema.py::TestTopLevelScalarSchemaGate::test_must_still_pass_this_repos_own_frob_toml
- tests/unit/test_toplevel_scalar_schema.py::TestTopLevelScalarSchemaGate::test_no_schema_declared_is_unresolved_not_empty
- tests/unit/test_toplevel_scalar_schema.py::TestTopLevelScalarSchemaGate::test_unresolvable_schema_dotted_path_is_unresolved
- tests/unit/test_toplevel_scalar_schema.py::TestTopLevelScalarSchemaGate::test_non_set_non_callable_schema_value_is_unresolved
- tests/unit/test_toplevel_scalar_schema.py::TestTopLevelScalarSchemaGate::test_no_frob_toml_is_unresolved
- tests/unit/test_toplevel_scalar_schema.py::TestTopLevelScalarSchemaGate::test_table_headers_are_never_flagged
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 268fe5437285ff4f31030af8fab35c82819fec6b
---
Validate the two top-level SCALAR keys (min_frob_version, check_base --
no enclosing table at all) against a declared schema. Readers:
frob.app._config_meta / frob.app.config. Structurally different from
every other T-2390 child (no [table] to iterate, no array-of-records) --
the schema declaration here names a flat set of top-level scalar key
names rather than a table's own leaf keys; do not force this into the
same per-table shape the other children use if it does not fit, per the
epic's own "if it doesn't fit, tell the coordinator" guidance -- this is
small enough that ANY reasonable shape is fine, just keep it consistent
with the module:symbol resolver idiom the rest of the epic uses.

Part of T-2390's epic decomposition -- see T-2390's body for the full
disjoint-readers finding and sibling children.