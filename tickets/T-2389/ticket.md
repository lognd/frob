---
id: T-2389
title: retarget hardcoded src/frob/ literal in _env_var_docs.py and _root_asset_dirs.py
  to the T-2195 source-root resolver
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_env_var_docs.py
- src/frob/gates/_root_asset_dirs.py
- tests/unit/gates/test_env_var_docs.py
- tests/unit/gates/test_root_asset_dirs.py
- src/frob/gates/_walk_lint.py
- tests/unit/gates/test_walk_lint.py
- src/frob/lang/_nodes.py
- src/frob/lang/__init__.py
- tests/test_gates.py
- docs/modules/gates.md
- rapid-debt.jsonl
evidence_scope:
- tests/test_walk_lint_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_walk_lint.py
  reason: T-2388's Done report found _walk_lint.py::tracked_python_files_for_gate
    hardcodes 'git ls-files -- src/frob' -- the same literal-package-path class this
    ticket already retargets, one layer below every gate (PORT001/WALK001/RENDER001
    alike) that reuses this shared helper to enumerate tracked files; folding in per
    coordinator instruction (2026-08-18) rather than filing a fourth sibling
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/gates/test_walk_lint.py
  reason: T-2388's Done report found _walk_lint.py::tracked_python_files_for_gate
    hardcodes 'git ls-files -- src/frob' -- the same literal-package-path class this
    ticket already retargets, one layer below every gate (PORT001/WALK001/RENDER001
    alike) that reuses this shared helper to enumerate tracked files; folding in per
    coordinator instruction (2026-08-18) rather than filing a fourth sibling
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/lang/_nodes.py
  reason: the fix promotes _declared_python_source_roots (T-2195) plus a new declared-package-name/prefix
    helper to a single public home in frob.lang -- both gates and PORT001 (T-2388)
    need one shared resolver, not a second private copy per NO DUPLICATION
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/lang/__init__.py
  reason: the fix promotes _declared_python_source_roots (T-2195) plus a new declared-package-name/prefix
    helper to a single public home in frob.lang -- both gates and PORT001 (T-2388)
    need one shared resolver, not a second private copy per NO DUPLICATION
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_gates.py
  reason: ENV001/ROOT001's own regression tests live in tests/test_gates.py, not the
    per-file test files the initial scope declared -- the retarget fix requires every
    existing fixture to gain a pyproject.toml (declared_project_package_name has no
    fallback, per T-2391 fail-loudly) plus new must-now-fire fixtures for a non-frob
    package
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/gates.md
  reason: T-2389 own ENV001/ROOT001 doc update, closing AFFECT001 the retarget introduced
  actor: logan
  at: '2026-08-18'
- op: add
  glob: rapid-debt.jsonl
  reason: prior land-attempt commits in this worktree recorded rapid-debt entries
    for T-2389; land-owned telemetry appended by frob itself, not hand-edited
  actor: logan
  at: '2026-08-18'
evidence:
- tests/test_gates.py::TestRootAssetDirGate::test_unreferenced_root_directory_fires
- tests/test_gates.py::TestRootAssetDirGate::test_unreferenced_root_directory_fires_for_a_differently_named_project
- tests/test_gates.py::TestRootAssetDirGate::test_directory_referenced_under_src_frob_is_silent
- tests/test_gates.py::TestRootAssetDirGate::test_directory_referenced_in_pyproject_is_silent
- tests/test_gates.py::TestRootAssetDirGate::test_directory_with_external_reader_declaration_is_silent
- tests/test_gates.py::TestRootAssetDirGate::test_makefile_referenced_directory_is_silent
- tests/test_gates.py::TestRootAssetDirGate::test_allowlisted_directories_are_silent
- tests/test_gates.py::TestRootAssetDirGate::test_src_and_tests_dirs_are_never_flagged
- tests/test_gates.py::TestRootAssetDirGate::test_non_git_root_is_silent
- tests/test_gates.py::TestRootAssetDirGate::test_missing_pyproject_is_unresolved_not_a_clean_pass
- tests/test_gates.py::TestEnvVarDocGate::test_undocumented_env_var_fires
- tests/test_gates.py::TestEnvVarDocGate::test_undocumented_env_var_fires_for_a_differently_named_project
- tests/test_gates.py::TestEnvVarDocGate::test_documented_by_literal_string_is_silent
- tests/test_gates.py::TestEnvVarDocGate::test_documented_by_constant_name_is_silent
- tests/test_gates.py::TestEnvVarDocGate::test_file_scoped_waiver_covers_it
- tests/test_gates.py::TestEnvVarDocGate::test_non_frob_env_prefixed_constants_are_ignored
- tests/test_gates.py::TestEnvVarDocGate::test_no_env_assignments_is_silent
- tests/test_gates.py::TestEnvVarDocGate::test_non_git_root_is_silent
- tests/test_gates.py::TestEnvVarDocGate::test_missing_pyproject_is_unresolved_not_a_clean_pass
- tests/test_walk_lint_gate.py::TestRglob::test_raw_rglob_fires
designated_repro_test: tests/test_gates.py::TestEnvVarDocGate::test_undocumented_env_var_fires_for_a_differently_named_project
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Child of T-2384 (source-root retarget half, group 1 of N -- narrow scope
per epic sequencing instruction, not a giant single ticket).

_env_var_docs.py:72 skips every tracked path not starting "src/frob/" --
silent-pass off-repo (ENVDOC reports zero for a src/lograder/ package).
Also hardcodes the FROB_ env-var prefix (same class: derive from project
name, not a literal). _root_asset_dirs.py:112's _referenced_in_src scans
only src/frob/** -- false-positive off-repo (legitimately referenced dirs
reported unreferenced).

Fix: promote frob.lang._nodes._declared_python_source_roots (T-2195) to a
single public home with a repo-relative-prefix form suitable for these
startswith sites; retarget both literals to it; derive env-var prefix from
project name.

Verification: must-now-fire fixture (src-layout project, package name !=
frob, a real ENVDOC/asset-dir violation the gate previously missed) AND
must-still-pass control (this repo's own pre-change finding count
unchanged).