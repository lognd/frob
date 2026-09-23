---
id: T-draft-0006b3a1
title: 'self-model cascade: sys003/conform-eval-needle/sys_gate_zero_violations/selfconform
  x2/packs/logging-integration/scaffold_dx x2 fail on current dev tip'
state: queued
kind: bug
origin: human
created: '2026-09-23'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/system/test_frob_self_model.py
- tests/unit/strata/test_sys003_calibration.py
- tests/unit/strata/test_conform_eval_needle.py
- tests/unit/strata/test_selfconform.py
- tests/unit/strata/test_packs.py
- tests/integration/test_logging_integration.py
- tests/system/test_scaffold_dx.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 35863437945 (ubuntu+macos, dev 08b02016db) -- 8 remaining individual failures not yet triaged to root cause on this pass, host under heavy concurrent-agent load (9+ implementers running frob check self-scans, load avg ~30-40) prevented completing the self-scan-heavy tests within a 10-minute budget: tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations, tests/unit/strata/test_sys003_calibration.py::TestSys003ZeroOnFrobsOwnRepo::test_sys003_zero_against_live_repo_design, tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch::test_real_repo_design_selfconform_has_no_eval_gap, tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant + TestCoverageTotality::test_repo_unrestricted_scan_is_clean, tests/unit/strata/test_packs.py::TestAutoInjection::test_trusted_component_without_pack_gets_it_injected, tests/integration/test_logging_integration.py::test_get_logger_end_to_end_emits_a_configured_record, tests/system/test_scaffold_dx.py::test_python_toolchain_scaffold_passes_check_immediately[python-tool] + test_hyphenated_name_scaffold_installs_and_console_script_runs. Prior triage on an earlier CI run found: (a) the scaffold_dx pair is T-5107 (PYTHONPATH leak into the nested uv run pytest subprocess) -- re-verify T-5107 is still queued/unfixed before assuming this is the same; (b) the selfconform/sys003/conform-eval-needle/sys_gate_zero_violations cluster previously matched T-5214 (narrative strata declarations) exactly -- re-verify against the CURRENT finding set since T-5300/T-5303 (css/scss/html/javascript/vue) may have added a SECOND, similar design/frob.strata declaration gap layered on top of T-5214's original narrative one; (c) test_trusted_component_without_pack_gets_it_injected and the logging-integration test were NOT previously seen failing and need fresh triage. Whoever picks this up: re-run each test individually when host load is low, check T-5107/T-5214 status first to avoid duplicating, and split into narrower tickets per distinct root cause once triaged.