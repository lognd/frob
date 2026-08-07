---
id: T-1350
title: 'TEST005 burn-down: src/frob/perf -- honest remainder after T-1293 false-close
  (65 findings)'
state: done
kind: feature
origin: agent
created: '2026-07-31'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/perf/**
- tests/unit/perf/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/perf/test_harness_main_branches.py::TestHarnessMainShortArgv::test_missing_target_returns_2
- tests/unit/perf/test_harness_main_branches.py::TestHarnessMainShortArgv::test_no_argv_at_all_returns_2
- tests/unit/perf/test_harness_main_branches.py::TestHarnessMainModuleDispatch::test_dash_m_runs_module_and_exits_clean
- tests/unit/perf/test_harness_main_branches.py::TestHarnessMainExitCodeNormalization::test_int_exit_code_passes_through
- tests/unit/perf/test_harness_main_branches.py::TestHarnessMainExitCodeNormalization::test_none_exit_code_normalizes_to_zero
- tests/unit/perf/test_harness_main_branches.py::TestHarnessMainExitCodeNormalization::test_non_int_exit_code_normalizes_to_one
- tests/unit/perf/test_harness_main_branches.py::TestHarnessMainExitCodeNormalization::test_clean_run_returns_zero_without_exit
- tests/unit/perf/test_serial_pools_import_failure.py::TestInstallSerialPoolsGatesImportError::test_import_error_still_patches_concurrent_futures_only
- tests/unit/perf/test_serial_pools_import_failure.py::TestInstallSerialPoolsGatesUnexpectedException::test_unexpected_import_time_exception_is_swallowed
designated_repro_test: null
acceptance:
- text: given an unscoped frob check --only test, when TEST005 lines under src/frob/perf
    are counted, then the count is materially below 65 and the report states the exact
    before and after
  evidence:
  - tests/unit/perf/test_harness_main_branches.py::TestHarnessMainExitCodeNormalization::test_int_exit_code_passes_through
threat: null
component: perf
---
Successor to T-1293, which was closed prematurely on 2026-07-31.

WHAT HAPPENED: T-1293 ("TEST005 burn-down: src/frob/perf, 64 findings") landed at cfbbb938 having fixed exactly ONE finding (load_ratchet_findings' two fail-open branches). The agent reported "0 TEST005 findings in src/frob/perf" and disclosed, in good faith, that it could not reproduce the ticket's baseline. A coordinator re-measure immediately after the land shows 65 TEST005 findings still outstanding in the package, including src/frob/perf/_harness.py::main at 3.0% branch coverage -- the very symbol the agent had concluded was "81% covered, well-covered".

ROOT CAUSE: the agent measured with a locally scoped "pytest --cov=src/frob/perf" over that package's own tests, and with "frob check --only test --ticket T-1293" (which filters to the ticket's declared SCOPE, narrower than the package). Neither is what TEST005 reads -- the gate is computed from the REPO-WIDE coverage stamp produced by "make coverage". The agent explicitly noted a full-repo coverage run was "coordinator-only per the playbook" and skipped it, so it had no way to see its real progress and reported a scoped number as a package number. The agent's disclosure was honest; the measurement was wrong.

THE WORK: the original burn-down, honestly measured. 65 findings remain. Worst offenders at time of filing: _harness.py::main 3.0%, _advisories.py::external_call_advisories 4.0%, _advisories.py::nested_loop_fanin_advisories 5.9%, _heat.py::heat 7.1%, _heat.py::render_bar 14.3%, _heat.py::join_smells 33.3%.

MEASURE CORRECTLY: "timeout 540 uv run frob check --only test" (unscoped) and grep TEST005 lines under src/frob/perf. That is the same source the gate uses and it costs ~5s. Do NOT use a scoped pytest --cov run or a --ticket-filtered check to claim completion.

Partial progress is acceptable and expected; report honest before/after and file a further successor for any remainder. Do not close this while the package still shows a large count.