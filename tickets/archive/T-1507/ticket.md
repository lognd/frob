---
id: T-1507
title: 'TEST005 burn-down: src/frob/check/_native.py and _python.py module-line floor
  (T-1309 follow-up)'
state: done
kind: feature
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/check/_native.py
- src/frob/check/_python.py
- tests/unit/test_check_native_cargo_runners.py
- tests/unit/test_check.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_check.py::TestCheckResultCounts::test_total_errors_sums_across_results
- tests/unit/test_check.py::TestCheckResultCounts::test_total_warnings_sums_across_results
- tests/unit/test_check.py::TestCheckResultCounts::test_zero_results_is_zero
- tests/unit/test_check.py::TestRunCheck::test_all_stages_skipped_returns_empty_result_for_root
- tests/unit/test_check.py::TestRunCheckCpp::test_all_stages_skipped_returns_empty_result
- tests/unit/test_check.py::TestRunCheckCpp::test_gates_stage_runs_by_default
- tests/unit/test_check.py::TestRunCheckRust::test_all_stages_skipped_returns_empty_result
- tests/unit/test_check.py::TestRunCheckRust::test_gates_stage_runs_by_default
- tests/unit/test_check.py::TestRunCheckRust::test_check_clippy_fmt_test_stages_all_run_and_append
- tests/unit/test_check.py::TestRunCheckTs::test_all_stages_skipped_returns_empty_result
- tests/unit/test_check.py::TestRunCheckTs::test_gates_stage_runs_by_default
- tests/unit/test_check.py::TestRunCheckTs::test_tsc_eslint_prettier_vitest_stages_all_run_and_append
- tests/unit/test_check.py::TestDispatchCheckThreadsGateSelectors::test_cpp_dispatch_threads_selectors
- tests/unit/test_check.py::TestDispatchCheckThreadsGateSelectors::test_cpp_dispatch_default_selectors_unchanged
- tests/unit/test_check.py::TestDispatchCheckThreadsGateSelectors::test_rust_dispatch_threads_selectors
- tests/unit/test_check.py::TestDispatchCheckThreadsGateSelectors::test_rust_dispatch_default_selectors_unchanged
- tests/unit/test_check.py::TestDispatchCheckThreadsGateSelectors::test_ts_dispatch_threads_selectors
- tests/unit/test_check.py::TestDispatchCheckThreadsGateSelectors::test_ts_dispatch_default_selectors_unchanged
- tests/unit/test_check.py::TestDetectProjectType::test_cargo_toml_is_rust
- tests/unit/test_check.py::TestDetectProjectType::test_cmakelists_is_cpp
- tests/unit/test_check.py::TestDetectProjectType::test_pyproject_is_python
- tests/unit/test_check.py::TestDetectProjectType::test_package_json_and_tsconfig_is_typescript
- tests/unit/test_check.py::TestDetectProjectType::test_package_json_alone_is_typescript
- tests/unit/test_check.py::TestDetectProjectType::test_no_sentinel_is_unknown
- tests/unit/test_check.py::TestDetectProjectType::test_bare_py_file_no_pyproject_is_python
- tests/unit/test_check.py::TestRunGatesQueueFailure::test_malformed_tickets_md_is_hard_error_not_silent_skip
- tests/unit/test_check.py::TestDerivedStateIntegrityGate::test_corrupt_artifact_fails_closed_before_any_stage_runs
- tests/unit/test_check.py::TestDerivedStateIntegrityGate::test_absent_artifact_is_not_a_violation
- tests/unit/test_check.py::TestRunGatesDelta::test_no_baseline_falls_back_to_full_set_with_warning
- tests/unit/test_check.py::TestRunGatesDelta::test_stale_baseline_falls_back_to_full_set_with_warning
- tests/unit/test_check.py::TestRunGatesCacheWiring::test_gate_cache_enabled_default_true
- tests/unit/test_check.py::TestRunGatesCacheWiring::test_gate_cache_enabled_false_when_no_cache_true
- tests/unit/test_check.py::TestRunGatesCacheWiring::test_gate_cache_enabled_false_when_env_var_set
- tests/unit/test_check.py::TestRunGatesCacheWiring::test_run_gates_passes_use_cache_true_by_default
- tests/unit/test_check.py::TestRunGatesCacheWiring::test_run_gates_no_cache_forces_use_cache_false
- tests/unit/test_check.py::TestSummarySeverityHonesty::test_warn_only_gate_summary_splits_errors_and_warnings
- tests/unit/test_check.py::TestSummarySeverityHonesty::test_cycle_summary_splits_by_severity
- tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_dup001_waived_group_excluded_from_headline_but_listed
- tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_dup001_partial_group_waiver_does_not_hide_whole_group
- tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_dup001_waiver_on_shared_symbol_does_not_hide_distinct_superset_group
- tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_dup001_waiving_every_fragment_of_superset_group_waives_it_too
- tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_dup001_unwaived_group_still_counts
- tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_dup001_waiver_above_nested_closure_covers_it_via_enclosing_method
- tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_arch001_waived_long_function_excluded_from_headline_but_listed
- tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_arch001_unwaived_long_function_still_counts
- tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_arch_stage_uses_calibrated_default_not_library_default
- tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_arch_stage_respects_explicit_frob_toml_override
- tests/unit/test_check.py::test_check_run_check_arch_integration
- tests/unit/test_check.py::TestCollectResultsLogLevelRace::test_racing_tasks_restore_original_stdout_handler_level
- tests/unit/test_check.py::TestCollectResultsLogLevelRace::test_all_none_tasks_still_restore_level
- tests/unit/test_check.py::TestCheckBuildsGraphOnce::test_run_check_calls_build_graph_exactly_once
- tests/unit/test_check.py::TestDerivedStateLockWiring::test_run_check_holds_shared_lock_across_precheck_and_stages
- tests/unit/test_check.py::TestDerivedStateLockWiring::test_run_check_precheck_failure_short_circuits_under_lock
- tests/unit/test_check.py::TestDerivedStateLockWiring::test_run_check_cpp_holds_shared_lock_across_precheck_and_stages
- tests/unit/test_check.py::TestDerivedStateLockWiring::test_run_check_cpp_build_failure_skips_tests_under_held_lock
- tests/unit/test_check.py::TestDerivedStateLockWiring::test_run_check_rust_holds_shared_lock_across_precheck_and_stages
- tests/unit/test_check.py::TestDerivedStateLockWiring::test_run_check_ts_holds_shared_lock_across_precheck_and_stages
- tests/unit/test_check.py::TestScopeDisclosure::test_only_names_the_gate_families_it_did_not_run
- tests/unit/test_check.py::TestScopeDisclosure::test_ticket_flag_notes_which_families_are_actually_diff_scoped
- tests/unit/test_check.py::TestScopeDisclosure::test_full_unfiltered_run_adds_no_disclosure
- tests/unit/test_check.py::TestRunRuffRealPaths::test_success_parses_ruff_json_and_appends_format_result
- tests/unit/test_check.py::TestRunRuffRealPaths::test_missing_binary_yields_two_typed_results
- tests/unit/test_check.py::TestRunRuffRealPaths::test_kill_switch_disabled_yields_two_typed_results
- tests/unit/test_check.py::TestRuffFormatResultRealPaths::test_all_formatted_is_clean_pass
- tests/unit/test_check.py::TestRuffFormatResultRealPaths::test_would_reformat_lines_produce_diagnostics
- tests/unit/test_check.py::TestRuffFormatResultRealPaths::test_missing_binary_is_typed_result
- tests/unit/test_check.py::TestRuffFormatResultRealPaths::test_kill_switch_disabled
- tests/unit/test_check.py::TestRunTyRealPaths::test_success_parses_ty_output
- tests/unit/test_check.py::TestRunTyRealPaths::test_extra_search_path_added_when_src_dir_exists
- tests/unit/test_check.py::TestRunTyRealPaths::test_ty_toml_extra_paths_are_appended
- tests/unit/test_check.py::TestRunTyRealPaths::test_malformed_ty_toml_is_silently_ignored
- tests/unit/test_check.py::TestRunTyRealPaths::test_missing_binary_is_typed_result
- tests/unit/test_check.py::TestRunTyRealPaths::test_kill_switch_disabled
- tests/unit/test_check.py::TestRunTyRealPaths::test_file_root_scans_parent_dir
- tests/unit/test_check.py::TestBuildImportGraphAndCycleRealPaths::test_no_files_produces_empty_graph
- tests/unit/test_check.py::TestBuildImportGraphAndCycleRealPaths::test_local_import_adds_edge
- tests/unit/test_check.py::TestBuildImportGraphAndCycleRealPaths::test_excluded_dirs_are_skipped
- tests/unit/test_check.py::TestBuildImportGraphAndCycleRealPaths::test_run_cycle_no_cycles_is_clean_pass
- tests/unit/test_check.py::TestBuildImportGraphAndCycleRealPaths::test_run_cycle_mutual_import_detected
- tests/unit/test_check.py::TestRunBindRealPaths::test_no_bind_markers_is_none
- tests/unit/test_check.py::TestRunBindRealPaths::test_has_bind_markers_true_when_present
- tests/unit/test_check.py::TestRunBindRealPaths::test_has_bind_markers_false_when_absent
- tests/unit/test_check.py::TestRunBindRealPaths::test_has_bind_markers_survives_unreadable_file
- tests/unit/test_check.py::TestRunBindRealPaths::test_import_error_for_missing_bind_module_is_none
- tests/unit/test_check.py::TestRunBindRealPaths::test_bind_mismatch_diagnostics_maps_mismatches
- tests/unit/test_check.py::TestExportsRealPaths::test_missing_exports_flags_unexported_symbols
- tests/unit/test_check.py::TestExportsRealPaths::test_missing_exports_empty_when_all_present
- tests/unit/test_check.py::TestExportsRealPaths::test_exports_for_package_no_siblings_is_none
- tests/unit/test_check.py::TestExportsRealPaths::test_exports_for_package_tests_dir_is_exempt
- tests/unit/test_check.py::TestExportsRealPaths::test_exports_for_package_reports_missing_symbol
- tests/unit/test_check.py::TestExportsRealPaths::test_unexported_symbols_result_builds_note_diagnostics
- tests/unit/test_check.py::TestExportsRealPaths::test_run_exports_scans_every_init_file
- tests/unit/test_check.py::TestExportsRealPaths::test_run_exports_no_init_files_is_empty
- tests/unit/test_check_native_cargo_runners.py::TestRunCargoRealPaths::test_success_parses_cargo_json
- tests/unit/test_check_native_cargo_runners.py::TestRunCargoRealPaths::test_kill_switch_disabled
- tests/unit/test_check_native_cargo_runners.py::TestRunCargoRealPaths::test_unexpected_crash_is_typed_result
- tests/unit/test_check_native_cargo_runners.py::TestRunCargoFmtCheckRealPaths::test_all_formatted_is_clean_pass
- tests/unit/test_check_native_cargo_runners.py::TestRunCargoFmtCheckRealPaths::test_unformatted_lines_produce_warning_diagnostics
- tests/unit/test_check_native_cargo_runners.py::TestRunCargoFmtCheckRealPaths::test_kill_switch_disabled
- tests/unit/test_check_native_cargo_runners.py::TestRunCargoTestRealPaths::test_success_parses_cargo_json
- tests/unit/test_check_native_cargo_runners.py::TestRunCargoTestRealPaths::test_kill_switch_disabled
- tests/unit/test_check_native_cargo_runners.py::TestRunCargoTestRealPaths::test_unexpected_crash_is_typed_result
- tests/unit/test_check_native_cargo_runners.py::TestCmakeConfigureRealPaths::test_success_returns_none
- tests/unit/test_check_native_cargo_runners.py::TestCmakeConfigureRealPaths::test_nonzero_exit_returns_typed_result
- tests/unit/test_check_native_cargo_runners.py::TestCmakeConfigureRealPaths::test_missing_binary_is_typed_result
- tests/unit/test_check_native_cargo_runners.py::TestCmakeConfigureRealPaths::test_unexpected_crash_is_typed_result
- tests/unit/test_check_native_cargo_runners.py::TestCmakeConfigureRealPaths::test_kill_switch_disabled
- tests/unit/test_check_native_cargo_runners.py::TestRunCmakeBuildRealPaths::test_configure_failure_short_circuits
- tests/unit/test_check_native_cargo_runners.py::TestRunCmakeBuildRealPaths::test_build_success_reports_build_succeeded
- tests/unit/test_check_native_cargo_runners.py::TestRunCmakeBuildRealPaths::test_missing_binary_is_typed_result
- tests/unit/test_check_native_cargo_runners.py::TestRunCmakeBuildRealPaths::test_unexpected_crash_is_typed_result
- tests/unit/test_check_native_cargo_runners.py::TestRunCmakeBuildRealPaths::test_kill_switch_disabled
- tests/unit/test_check_native_cargo_runners.py::TestRunClangTidyCmakeRealPaths::test_no_compile_commands_is_none
- tests/unit/test_check_native_cargo_runners.py::TestRunClangTidyCmakeRealPaths::test_no_sources_is_none
- tests/unit/test_check_native_cargo_runners.py::TestRunClangTidyCmakeRealPaths::test_success_parses_clang_tidy_output
- tests/unit/test_check_native_cargo_runners.py::TestRunClangTidyCmakeRealPaths::test_missing_binary_is_typed_result
- tests/unit/test_check_native_cargo_runners.py::TestRunClangTidyCmakeRealPaths::test_kill_switch_disabled
- tests/unit/test_check_native_cargo_runners.py::TestRunClangTidyCmakeRealPaths::test_parse_failure_is_typed_crash_result
- tests/unit/test_check_native_cargo_runners.py::TestRunClangFormatRealPaths::test_no_sources_is_none
- tests/unit/test_check_native_cargo_runners.py::TestRunClangFormatRealPaths::test_all_formatted_is_clean_pass
- tests/unit/test_check_native_cargo_runners.py::TestRunClangFormatRealPaths::test_needs_format_produces_diagnostics
- tests/unit/test_check_native_cargo_runners.py::TestRunClangFormatRealPaths::test_missing_binary_is_typed_result
- tests/unit/test_check_native_cargo_runners.py::TestRunClangFormatRealPaths::test_kill_switch_disabled
- tests/unit/test_check_native_cargo_runners.py::TestRunCtestRealPaths::test_missing_build_dir_is_none
- tests/unit/test_check_native_cargo_runners.py::TestRunCtestRealPaths::test_success_parses_junit_report
- tests/unit/test_check_native_cargo_runners.py::TestRunCtestRealPaths::test_falls_back_to_text_parsing_without_junit
- tests/unit/test_check_native_cargo_runners.py::TestRunCtestRealPaths::test_malformed_junit_is_typed_crash_result
- tests/unit/test_check_native_cargo_runners.py::TestRunCtestRealPaths::test_missing_binary_is_typed_result
- tests/unit/test_check_native_cargo_runners.py::TestRunCtestRealPaths::test_unexpected_crash_is_typed_result
- tests/unit/test_check_native_cargo_runners.py::TestRunCtestRealPaths::test_kill_switch_disabled
- tests/unit/test_check_native_cargo_runners.py::TestFindTestBinaryFromCargoJson::test_finds_test_executable
- tests/unit/test_check_native_cargo_runners.py::TestFindTestBinaryFromCargoJson::test_ignores_non_test_artifacts
- tests/unit/test_check_native_cargo_runners.py::TestFindTestBinaryFromCargoJson::test_skips_malformed_json_lines
- tests/unit/test_check_native_cargo_runners.py::TestFindTestBinaryFromCargoJson::test_no_matching_message_is_none
- tests/unit/test_check_native_cargo_runners.py::TestRunCargoValgrindRealPaths::test_no_test_binary_found_is_none
- tests/unit/test_check_native_cargo_runners.py::TestRunCargoValgrindRealPaths::test_missing_cargo_binary_is_typed_result
- tests/unit/test_check_native_cargo_runners.py::TestRunCargoValgrindRealPaths::test_build_kill_switch_disabled
- tests/unit/test_check_native_cargo_runners.py::TestRunCargoValgrindRealPaths::test_valgrind_success_parses_output
- tests/unit/test_check_native_cargo_runners.py::TestRunCargoValgrindRealPaths::test_missing_valgrind_binary_is_typed_result
- tests/unit/test_check_native_cargo_runners.py::TestRunCargoValgrindRealPaths::test_run_kill_switch_disabled
designated_repro_test: null
threat: null
component: null
---
T-1309's 5 TEST005 findings in src/frob/check: 2 branch findings
(run_check_rust, run_check_ts) and 3 module-line findings (_native.py
22.7%, _python.py 65.0%, _ts.py 53.5%). T-1309 closed run_check_rust,
run_check_ts, and _ts.py (module line now 82% via
tests/unit/test_check_ts_runners.py's real tsc/eslint/prettier/vitest
success + kill-switch-disabled + timeout path tests).

_native.py and _python.py remain below the 70% module_line_cov floor:
- _native.py (24% even after adding cargo-runner tests
  tests/unit/test_check_native_cargo_runners.py): most of the file's
  225 lines are the cmake/clang-tidy/clang-format/ctest/valgrind runners
  (lines 43-264), which this ticket's cargo-only tests did not touch --
  a substantially larger test-writing job (mocking guarded_subprocess_run
  across ~8 more functions) than fit in this dispatch.
- _python.py (60%, 388 lines): scattered gaps across ruff/ty/pytest
  runner functions and result-formatting helpers -- also needs a
  dedicated pass, not attempted here.

Filed as a follow-up so this known-remaining work is tracked rather than
silently dropped when T-1309 closes on its completed subset.