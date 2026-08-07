---
id: T-0629
title: 'std.host windows: binPath/ImagePath vocabulary so install.ps1 can create the
  SCM service, not just harden it'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0261
parent: T-0254
tier: ticket
sprint: null
scope:
- strata-core/src/parse.rs
- src/frob/strata/_host.py
- src/frob/deploy/_generate_windows.py
- tests/unit/strata/
- tests/unit/deploy/
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- strata-core/src/parse/mod.rs::tests::parses_node_bin_path_clause
- strata-core/src/parse/mod.rs::tests::parses_node_bin_path_clause_without_args
- strata-core/src/parse/mod.rs::tests::parses_store_bin_path_clause
- tests/unit/strata/test_host.py::TestHostAttrs::test_desugars_bin_path
- tests/unit/strata/test_host.py::TestHostManifestWindows::test_reads_bin_path
- tests/unit/strata/test_host.py::TestHostManifestWindows::test_bin_path_defaults_none
- tests/unit/deploy/test_generate_windows.py::TestInstall::test_service_not_present_notes_missing_bin_path
- tests/unit/deploy/test_generate_windows.py::TestInstall::test_creates_service_when_bin_path_declared
- tests/unit/deploy/test_generate_windows.py::TestInstall::test_creates_service_without_args
- strata-core/src/parse/mod.rs::tests::parses_node_bin_path_clause
- strata-core/src/parse/mod.rs::tests::parses_node_bin_path_clause_without_args
- strata-core/src/parse/mod.rs::tests::parses_store_bin_path_clause
designated_repro_test: null
acceptance:
- text: GIVEN a windows node declaring service with a binPath WHEN install.ps1 is
    generated THEN it idempotently creates the SCM service with that image path before
    hardening AND uninstall.ps1 deletes it
  evidence:
  - strata-core/src/parse/mod.rs::tests::parses_node_bin_path_clause
  - strata-core/src/parse/mod.rs::tests::parses_node_bin_path_clause_without_args
  - strata-core/src/parse/mod.rs::tests::parses_store_bin_path_clause
  - tests/unit/strata/test_host.py::TestHostAttrs::test_desugars_bin_path
  - tests/unit/strata/test_host.py::TestHostManifestWindows::test_reads_bin_path
  - tests/unit/strata/test_host.py::TestHostManifestWindows::test_bin_path_defaults_none
  - tests/unit/deploy/test_generate_windows.py::TestInstall::test_service_not_present_notes_missing_bin_path
  - tests/unit/deploy/test_generate_windows.py::TestInstall::test_creates_service_when_bin_path_declared
  - tests/unit/deploy/test_generate_windows.py::TestInstall::test_creates_service_without_args
  - strata-core/src/parse/mod.rs::tests::parses_node_bin_path_clause
  - strata-core/src/parse/mod.rs::tests::parses_node_bin_path_clause_without_args
  - strata-core/src/parse/mod.rs::tests::parses_store_bin_path_clause
threat: null
component: null
---
T-0264's windows generator hardens an existing SCM service (SID type, privileges via sc.exe config) but cannot CREATE one -- std.host has no binPath/ImagePath (executable path + arguments) vocabulary, so sc.exe create is impossible from the model. T-0254's epic text says the install sequence registers the Windows Service; full-install-from-zero needs the vocabulary. Add the grammar clause (parse.rs node/store symmetry per T-0261 precedent), HostManifest read-back, and wire generate_windows_install_script to sc.exe create idempotently when binPath is declared. Flagged by T-0264's reviewer so the epic's full-install intent is not silently lost.