## Done report

Changed:
src/frob/deploy/_generate.py::generate_status_script (tests only, no source change)
src/frob/deploy/_generate.py::generate_uninstall_script (tests only, no source change)
src/frob/deploy/_drift.py::deploy_drift_violations (tests only, no source change)
src/frob/deploy/_conform.py::extract_mutation_surface (tests only, no source change)
src/frob/deploy/_conform.py::deploy_conformance_violations (tests only, no source change)
src/frob/deploy/_vm_runner.py::run_vm_audit (module docstring updated to reflect new mocked-subprocess unit coverage; no behavior change)
src/frob/app/deploy_runner.py::run (tests only, no source change)
tests/unit/deploy/test_generate.py (added TestStatus.test_no_units_declared, test_manifest_present_but_not_a_unit, test_unit_with_no_listens_ports; TestUninstall.test_empty_model, test_node_with_no_unit_no_owns_no_runs_as)
tests/unit/deploy/test_drift.py (added test_no_model_loads, test_partial_committed, test_malformed_strata_file_yields_no_model, test_bad_frob_toml_falls_back_to_default_design_dir, test_custom_design_dir_from_frob_toml)
tests/unit/deploy/test_conform.py (added test_unterminated_quote_is_parse_error, test_no_model_loads, test_partial_committed)
tests/unit/deploy/test_vm_runner.py (added TestFullSequence.test_run_vm_audit_runs_full_sequence and test_run_vm_audit_propagates_ssh_error, mocking subprocess.run at the module boundary)
tests/unit/deploy/test_deploy_runner.py (new file: TestDispatch, TestGenerate, TestAudit covering run()'s full dispatch/generate/audit CLI surface)

Evidence (pytest node ids, from a fresh `pytest --collect-only` pass, 59 tests total across the touched files):
tests/unit/deploy/test_generate.py::TestStatus::test_no_units_declared
tests/unit/deploy/test_generate.py::TestStatus::test_manifest_present_but_not_a_unit
tests/unit/deploy/test_generate.py::TestStatus::test_unit_with_no_listens_ports
tests/unit/deploy/test_generate.py::TestUninstall::test_empty_model
tests/unit/deploy/test_generate.py::TestUninstall::test_node_with_no_unit_no_owns_no_runs_as
tests/unit/deploy/test_drift.py::TestDrift::test_no_model_loads
tests/unit/deploy/test_drift.py::TestDrift::test_partial_committed
tests/unit/deploy/test_drift.py::TestDrift::test_malformed_strata_file_yields_no_model
tests/unit/deploy/test_drift.py::TestDrift::test_bad_frob_toml_falls_back_to_default_design_dir
tests/unit/deploy/test_drift.py::TestDrift::test_custom_design_dir_from_frob_toml
tests/unit/deploy/test_conform.py::TestExtract::test_unterminated_quote_is_parse_error
tests/unit/deploy/test_conform.py::TestConform::test_no_model_loads
tests/unit/deploy/test_conform.py::TestConform::test_partial_committed
tests/unit/deploy/test_vm_runner.py::TestFullSequence::test_run_vm_audit_runs_full_sequence
tests/unit/deploy/test_vm_runner.py::TestFullSequence::test_run_vm_audit_propagates_ssh_error
tests/unit/deploy/test_deploy_runner.py::TestDispatch::test_unrecognized_command_prints_usage_and_exits
tests/unit/deploy/test_deploy_runner.py::TestDispatch::test_no_command_prints_usage_and_exits
tests/unit/deploy/test_deploy_runner.py::TestGenerate::test_generate_no_model_exits_1
tests/unit/deploy/test_deploy_runner.py::TestGenerate::test_generate_writes_files
tests/unit/deploy/test_deploy_runner.py::TestGenerate::test_generate_check_clean_no_exit
tests/unit/deploy/test_deploy_runner.py::TestGenerate::test_generate_check_missing_files_exits_1
tests/unit/deploy/test_deploy_runner.py::TestGenerate::test_generate_check_stale_file_exits_1
tests/unit/deploy/test_deploy_runner.py::TestAudit::test_audit_missing_vm_exits_1
tests/unit/deploy/test_deploy_runner.py::TestAudit::test_audit_missing_ssh_host_exits_1
tests/unit/deploy/test_deploy_runner.py::TestAudit::test_audit_missing_ssh_key_exits_1
tests/unit/deploy/test_deploy_runner.py::TestAudit::test_audit_no_model_exits_1
tests/unit/deploy/test_deploy_runner.py::TestAudit::test_audit_skipped_exits_2
tests/unit/deploy/test_deploy_runner.py::TestAudit::test_audit_passed_writes_attestation_no_exit
tests/unit/deploy/test_deploy_runner.py::TestAudit::test_audit_failed_exits_1
(full list of all 59 collected node ids across the 5 touched test files verified via
`uv run pytest --collect-only tests/unit/deploy/test_generate.py tests/unit/deploy/test_drift.py
tests/unit/deploy/test_conform.py tests/unit/deploy/test_vm_runner.py tests/unit/deploy/test_deploy_runner.py`)

Filed: none

Gates:
`uv run frob check --only test` -- 0 findings mention any of _generate.py, _drift.py, _conform.py,
_vm_runner.py, or deploy_runner.py (before: 10 findings across these 5 files, after: 0).
`uv run frob check` (full) -- `0 errors, 13 warnings, 222 waived`; the 13 warnings/notes are all
`pass`-status frob-arch/frob-exports advisories in unrelated modules (pre-existing, not TEST005, not
introduced by this change; e.g. `frob-arch` long-function/abstraction-opportunity notes in
`tests/test_gates.py`/`tests/unit/test_check.py`, `frob-exports` missing-from-`__init__.py` notes across
several unrelated packages).

TEST005 (deploy files) before: 10  after: 0
