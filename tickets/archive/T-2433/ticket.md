---
id: T-2433
title: 'T-2390 child: validate [arch] table against a declared schema'
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: high
parent: T-2390
tier: story
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_arch_table_schema.py
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
no_scope_declared: false
no_scope_declared_reason: null
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
- tests/unit/test_arch_table_schema.py::TestArchSchemaGate::test_arch_known_keys_matches_load_arch_configs_own_defaults
- tests/unit/test_arch_table_schema.py::TestArchSchemaGate::test_must_now_fire_reports_the_undeclared_key
- tests/unit/test_arch_table_schema.py::TestArchSchemaGate::test_must_still_pass_this_repos_own_frob_toml
- tests/unit/test_arch_table_schema.py::TestArchSchemaGate::test_nested_layering_subtable_is_never_flagged
- tests/unit/test_arch_table_schema.py::TestArchSchemaGate::test_no_schema_declared_defaults_to_frobs_own_keys_must_fire
- tests/unit/test_arch_table_schema.py::TestArchSchemaGate::test_unresolvable_schema_dotted_path_is_unresolved
- tests/unit/test_arch_table_schema.py::TestArchSchemaGate::test_non_set_non_callable_schema_value_is_unresolved
- tests/unit/test_arch_table_schema.py::TestArchSchemaGate::test_no_frob_toml_is_unresolved
- tests/unit/test_arch_table_schema.py::TestArchSchemaGate::test_no_arch_table_at_all_is_clean_not_error
designated_repro_test: null
evidence_changes:
- old_node: tests/unit/test_arch_table_schema.py::TestArchSchemaGate::test_no_schema_declared_is_unresolved_not_empty
  new_node: tests/unit/test_arch_table_schema.py::TestArchSchemaGate::test_no_schema_declared_defaults_to_frobs_own_keys_must_fire
  reason: 'T-3273 renamed this fixture: undeclared known_keys now defaults internally
    instead of reporting UNRESOLVED'
  actor: logan
  at: '2026-08-28'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 4f4d45f907786e0c9e65ddd6e409b70da1318dd8
---
Validate the `[arch]` table (9 leaves) against a declared schema.
Reader: frob.app._config_meta.load_arch_config -- hand-lists 10 named
keys (5 T-0373 thresholds + 5 T-0728 SRP/cohesion knobs) against its own
calibrated-defaults dict; a misspelled key (e.g. "max_fuction_lines",
this epic's own filing-time example) silently reverts to the built-in
default with no diagnostic.

Same required shape as every T-2390 child: module:symbol declared
schema (T-2397's resolve_dotted_symbol precedent), must-now-fire +
must-still-pass fixtures, Severity.UNRESOLVED (never silent) when no
schema is declared, portable (no hardcoded frob-specific reference).

Part of T-2390's epic decomposition -- see T-2390's body for the full
disjoint-readers finding and sibling children.