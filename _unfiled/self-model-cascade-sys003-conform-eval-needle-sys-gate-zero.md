+++
id = "01M35RZY8M2YGAPQSK9N9T3R0M"
title = "self-model cascade: sys003/conform-eval-needle/sys_gate_zero_violations/selfconform x2/packs/logging-integration/scaffold_dx x2 fail on current dev tip"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 5
reporter = "human"
created = "2026-09-23T00:00:00Z"
updated = "2026-09-23T00:00:02Z"
aliases = ["T-5396"]
labels = ["milestone:v0.534.0"]
scope = ["tests/system/test_frob_self_model.py", "tests/unit/strata/test_sys003_calibration.py", "tests/unit/strata/test_conform_eval_needle.py", "tests/unit/strata/test_selfconform.py", "tests/unit/strata/test_packs.py", "tests/integration/test_logging_integration.py", "tests/system/test_scaffold_dx.py"]
+++

CI run 35863437945 (ubuntu+macos, dev 08b02016db) -- 8 remaining individual failures not yet triaged to root cause on this pass, host under heavy concurrent-agent load (9+ implementers running frob check self-scans, load avg ~30-40) prevented completing the self-scan-heavy tests within a 10-minute budget: tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations, tests/unit/strata/test_sys003_calibration.py::TestSys003ZeroOnFrobsOwnRepo::test_sys003_zero_against_live_repo_design, tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch::test_real_repo_design_selfconform_has_no_eval_gap, tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant + TestCoverageTotality::test_repo_unrestricted_scan_is_clean, tests/unit/strata/test_packs.py::TestAutoInjection::test_trusted_component_without_pack_gets_it_injected, tests/integration/test_logging_integration.py::test_get_logger_end_to_end_emits_a_configured_record, tests/system/test_scaffold_dx.py::test_python_toolchain_scaffold_passes_check_immediately[python-tool] + test_hyphenated_name_scaffold_installs_and_console_script_runs. Prior triage on an earlier CI run found: (a) the scaffold_dx pair is T-5107 (PYTHONPATH leak into the nested uv run pytest subprocess) -- re-verify T-5107 is still queued/unfixed before assuming this is the same; (b) the selfconform/sys003/conform-eval-needle/sys_gate_zero_violations cluster previously matched T-5214 (narrative strata declarations) exactly -- re-verify against the CURRENT finding set since T-5300/T-5303 (css/scss/html/javascript/vue) may have added a SECOND, similar design/frob.strata declaration gap layered on top of T-5214's original narrative one; (c) test_trusted_component_without_pack_gets_it_injected and the logging-integration test were NOT previously seen failing and need fresh triage. Whoever picks this up: re-run each test individually when host load is low, check T-5107/T-5214 status first to avoid duplicating, and split into narrower tickets per distinct root cause once triaged.
