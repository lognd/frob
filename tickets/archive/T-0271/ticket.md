---
id: T-0271
title: 'fix(testing): rust collector treats virtual workspace root as one crate'
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/testing/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_testing.py::TestFindCrates::test_virtual_workspace_root_descends_to_members
- tests/test_testing.py::TestFindCrates::test_root_package_with_nested_workspace_members
- tests/test_testing.py::TestFindCrates::test_plain_single_crate_unchanged
- tests/test_testing.py::TestFindCrates::test_unparseable_manifest_keeps_old_behavior_and_warns
- tests/test_testing.py::TestIntegrationTestCollection::test_integration_module_path_to_symref_flat_case
- tests/test_testing.py::TestIntegrationTestCollection::test_find_integration_test_files_lists_and_skips_missing_dir
designated_repro_test: null
threat: null
component: null
---
`_find_crates` (`src/frob/testing/_collect.py`) stopped descent at the
first `Cargo.toml` found, so a cargo virtual workspace root (`[workspace]`
table, no `[package]` table -- exactly what lithos's and feldspar's root
`Cargo.toml` are) was treated as one crate: every collected rust node id
lost its crate-directory prefix and collided across member crates, making
correctly-scoped `frob:tests` bindings undischargeable in any workspace
repo (TEST001/TEST002). Separately, `cargo test --lib` never lists
`tests/*.rs` integration binaries, so `frob:tests` edges into a crate's
`tests/` files could never validate either (TEST003). Found while
adopting frob in lithos; full original analysis in that repo's
`FROBLEMS.md` (2026-07-18 entry).