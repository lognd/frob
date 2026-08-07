## Done report

Changed:
strata-core/src/parse/mod.rs::Parser::parse_node (bin_path clause)
strata-core/src/parse/mod.rs::Parser::parse_store (bin_path clause)
src/frob/strata/_host.py::HostManifest.bin_path
src/frob/strata/_host.py::HostManifest.bin_path_args
src/frob/strata/_host.py::_host_attrs
src/frob/strata/_host.py::_ParsedHostAttrs
src/frob/strata/_host.py::_parse_host_attrs
src/frob/strata/_host.py::host_manifest_for
src/frob/deploy/_generate_windows.py::_service_image_path
src/frob/deploy/_generate_windows.py::_install_service_hardening_block

Evidence: strata-core/src/parse/mod.rs::tests::parses_node_bin_path_clause, strata-core/src/parse/mod.rs::tests::parses_node_bin_path_clause_without_args, strata-core/src/parse/mod.rs::tests::parses_store_bin_path_clause, tests/unit/strata/test_host.py::TestHostAttrs::test_desugars_bin_path, tests/unit/strata/test_host.py::TestHostManifestWindows::test_reads_bin_path, tests/unit/strata/test_host.py::TestHostManifestWindows::test_bin_path_defaults_none, tests/unit/deploy/test_generate_windows.py::TestInstall::test_service_not_present_notes_missing_bin_path, tests/unit/deploy/test_generate_windows.py::TestInstall::test_creates_service_when_bin_path_declared, tests/unit/deploy/test_generate_windows.py::TestInstall::test_creates_service_without_args (all bound to acceptance[0] via `frob ticket evidence --accepts 0`). Full `cargo test --release` (123 passed) and full targeted pytest run (49 passed) both observed green after merging main (T-0933 check-lock fix) and a fresh `frob natives build`.

Filed: T-0941 (docs/modules/deploy.md's windows scope-cut prose is now stale re: binPath vocabulary; out of this ticket's declared scope to fix)

Gates: `frob check --ticket T-0629 --only cycle` clean; `--only exports` clean (pre-existing warnings elsewhere, none in scope); `--only dup` PASS (169 groups, 110 waived; 3 unwaived renamed-dup findings appear in src/frob/deploy/_generate_windows.py but sit entirely inside pre-existing functions this ticket did not touch -- `_install_service_account_block`/`_uninstall_service_account_block`, `_install_acl_block`, `_install_firewall_block` -- confirmed against the diff, not introduced here); `--only arch` PASS (76 warnings/233 suggestions, none referencing parse.rs/_host.py/_generate_windows.py); `--only lint` shows 3 pre-existing ruff-format warnings in unrelated files (_lock_ordering.py, test_gates.py, test_arch.py), not mine.
