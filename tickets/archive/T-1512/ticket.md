---
id: T-1512
title: 'TEST005 follow-up: _python.py module-line floor findings from T-1309 sweep'
state: done
kind: feature
origin: human
created: '2026-08-04'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/check/_python.py
- tests/unit/test_check.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/check/_python.py
  reason: narrowing empty scope to the exact _python.py TEST005 follow-up files, merged
    into T-1507's burn-down work
  actor: logan
  at: '2026-08-05'
- op: add
  glob: tests/unit/test_check.py
  reason: narrowing empty scope to the exact _python.py TEST005 follow-up files, merged
    into T-1507's burn-down work
  actor: logan
  at: '2026-08-05'
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
designated_repro_test: null
threat: null
component: null
---
Tracks the _python.py module-line coverage-floor findings surfaced during T-1309's run_check TEST005 sweep; split out so T-1309 could close on its own scope. Refiled: the original tracking draft T-1512 died in a removed worktree before landing.