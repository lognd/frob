## Done report

TEST005 module-line burn-down for src/frob/check/_native.py and _python.py
(T-1309 follow-up). Merged with T-1512 (the _python.py module-line
follow-up) since both targeted the same file's remaining gap; both
tickets close together.

Added real-behavior tests (no mocked-away logic, monkeypatched only at
the `guarded_subprocess_run`/import boundary) covering the previously
untested runner functions:

_native.py (tests/unit/test_check_native_cargo_runners.py): cmake
configure/build success+failure+missing-binary+crash+kill-switch paths,
clang-tidy (no compile db, no sources, success, missing binary,
kill-switch, malformed-output crash), clang-format (no sources, all
formatted, needs-format diagnostics, missing binary, kill-switch), ctest
(missing build dir, JUnit success, text-parse fallback, malformed JUnit
crash, missing binary, unexpected crash, kill-switch),
_find_test_binary_from_cargo_json (found/ignored/malformed/absent), and
_run_cargo_valgrind (no test binary, missing cargo, build kill-switch,
valgrind success, missing valgrind binary, run kill-switch).

_python.py (tests/unit/test_check.py): _run_ruff/_ruff_format_result
(success, would-reformat diagnostics, missing binary, kill-switch),
_run_ty (success, extra-search-path/--python wiring, ty.toml
extra-paths, malformed ty.toml tolerance, missing binary, kill-switch,
file-root parent-dir scan), _build_import_graph/_run_cycle (empty graph,
local-import edge, excluded-dir skip, no-cycle clean pass, mutual-import
cycle detection), _run_bind/_has_bind_markers/_bind_mismatch_diagnostics
(no markers, markers present, unreadable file, missing frob.bind import,
mismatch-to-diagnostic mapping), and
_missing_exports/_exports_for_package/_unexported_symbols_result/
_run_exports (present/missing symbol sets, no-siblings skip, tests/-dir
exemption, missing-symbol reporting, multi-package scan, no-init-files
empty result).

Measured coverage (pytest --cov, this ticket's own test files only):
- src/frob/check/_native.py: 225 stmts, 88% line coverage (up from 23%
  measured at ticket start) -- `pytest tests/unit/test_check_native_cargo_runners.py
  --cov=frob.check._native --cov-report=term-missing`
- src/frob/check/_python.py: 388 stmts, 90% line coverage (up from 56%
  measured with the same test set at ticket start) -- `pytest
  tests/unit/test_check.py --cov=frob.check._python --cov-report=term-missing`

Both comfortably clear the 70% module_line_cov TEST005 floor. Per playbook
section 6c/6d, this is a locally-scoped pytest --cov measurement, not a
full `make coverage` stamp -- the coordinator's next full-suite coverage
run is the authoritative TEST005 number; these numbers demonstrate the
fix, not a package-wide guarantee.

`frob check --only test --ticket T-1507`: 0 errors, 8 pre-existing
warnings (TEST003/TEST014 findings unrelated to this ticket's scope),
3 waived.
`frob check --land-parity`: clean -- 0 unscoped errors.
`ruff check`/`ruff format`: clean on all 4 touched files.

Filed: none (T-1509 and T-1508 were pre-filed before this dispatch;
no new out-of-scope work discovered).

### Changed
```
 design/frob.strata                            |   4 +-
 src/frob/dup/_legacy_cpp.py                   |  47 +-
 tests/unit/test_check.py                      | 476 +++++++++++++++++-
 tests/unit/test_check_native_cargo_runners.py | 530 ++++++++++++++++++-
 tests/unit/test_dup_legacy_cpp.py             |  83 ++-
 tickets.md                                    | 699 +++++++++++++++++++++++++-
 6 files changed, 1795 insertions(+), 44 deletions(-)
```

### Evidence
- `tests/unit/test_check.py::TestCheckResultCounts::test_total_errors_sums_across_results` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestCheckResultCounts::test_total_warnings_sums_across_results` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestCheckResultCounts::test_zero_results_is_zero` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunCheck::test_all_stages_skipped_returns_empty_result_for_root` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunCheckCpp::test_all_stages_skipped_returns_empty_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunCheckCpp::test_gates_stage_runs_by_default` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunCheckRust::test_all_stages_skipped_returns_empty_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunCheckRust::test_gates_stage_runs_by_default` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunCheckRust::test_check_clippy_fmt_test_stages_all_run_and_append` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunCheckTs::test_all_stages_skipped_returns_empty_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunCheckTs::test_gates_stage_runs_by_default` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunCheckTs::test_tsc_eslint_prettier_vitest_stages_all_run_and_append` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDispatchCheckThreadsGateSelectors::test_cpp_dispatch_threads_selectors` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDispatchCheckThreadsGateSelectors::test_cpp_dispatch_default_selectors_unchanged` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDispatchCheckThreadsGateSelectors::test_rust_dispatch_threads_selectors` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDispatchCheckThreadsGateSelectors::test_rust_dispatch_default_selectors_unchanged` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDispatchCheckThreadsGateSelectors::test_ts_dispatch_threads_selectors` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDispatchCheckThreadsGateSelectors::test_ts_dispatch_default_selectors_unchanged` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDetectProjectType::test_cargo_toml_is_rust` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDetectProjectType::test_cmakelists_is_cpp` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDetectProjectType::test_pyproject_is_python` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDetectProjectType::test_package_json_and_tsconfig_is_typescript` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDetectProjectType::test_package_json_alone_is_typescript` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDetectProjectType::test_no_sentinel_is_unknown` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDetectProjectType::test_bare_py_file_no_pyproject_is_python` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunGatesQueueFailure::test_malformed_tickets_md_is_hard_error_not_silent_skip` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDerivedStateIntegrityGate::test_corrupt_artifact_fails_closed_before_any_stage_runs` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDerivedStateIntegrityGate::test_absent_artifact_is_not_a_violation` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunGatesDelta::test_no_baseline_falls_back_to_full_set_with_warning` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunGatesDelta::test_stale_baseline_falls_back_to_full_set_with_warning` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunGatesCacheWiring::test_gate_cache_enabled_default_true` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunGatesCacheWiring::test_gate_cache_enabled_false_when_no_cache_true` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunGatesCacheWiring::test_gate_cache_enabled_false_when_env_var_set` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunGatesCacheWiring::test_run_gates_passes_use_cache_true_by_default` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunGatesCacheWiring::test_run_gates_no_cache_forces_use_cache_false` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestSummarySeverityHonesty::test_warn_only_gate_summary_splits_errors_and_warnings` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestSummarySeverityHonesty::test_cycle_summary_splits_by_severity` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_dup001_waived_group_excluded_from_headline_but_listed` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_dup001_partial_group_waiver_does_not_hide_whole_group` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_dup001_waiver_on_shared_symbol_does_not_hide_distinct_superset_group` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_dup001_waiving_every_fragment_of_superset_group_waives_it_too` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_dup001_unwaived_group_still_counts` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_dup001_waiver_above_nested_closure_covers_it_via_enclosing_method` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_arch001_waived_long_function_excluded_from_headline_but_listed` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_arch001_unwaived_long_function_still_counts` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_arch_stage_uses_calibrated_default_not_library_default` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDupArchWaiverAwareSummaries::test_arch_stage_respects_explicit_frob_toml_override` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::test_check_run_check_arch_integration` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestCollectResultsLogLevelRace::test_racing_tasks_restore_original_stdout_handler_level` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestCollectResultsLogLevelRace::test_all_none_tasks_still_restore_level` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestCheckBuildsGraphOnce::test_run_check_calls_build_graph_exactly_once` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDerivedStateLockWiring::test_run_check_holds_shared_lock_across_precheck_and_stages` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDerivedStateLockWiring::test_run_check_precheck_failure_short_circuits_under_lock` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDerivedStateLockWiring::test_run_check_cpp_holds_shared_lock_across_precheck_and_stages` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDerivedStateLockWiring::test_run_check_cpp_build_failure_skips_tests_under_held_lock` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDerivedStateLockWiring::test_run_check_rust_holds_shared_lock_across_precheck_and_stages` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDerivedStateLockWiring::test_run_check_ts_holds_shared_lock_across_precheck_and_stages` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestScopeDisclosure::test_only_names_the_gate_families_it_did_not_run` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestScopeDisclosure::test_ticket_flag_notes_which_families_are_actually_diff_scoped` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestScopeDisclosure::test_full_unfiltered_run_adds_no_disclosure` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunRuffRealPaths::test_success_parses_ruff_json_and_appends_format_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunRuffRealPaths::test_missing_binary_yields_two_typed_results` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunRuffRealPaths::test_kill_switch_disabled_yields_two_typed_results` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRuffFormatResultRealPaths::test_all_formatted_is_clean_pass` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRuffFormatResultRealPaths::test_would_reformat_lines_produce_diagnostics` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRuffFormatResultRealPaths::test_missing_binary_is_typed_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRuffFormatResultRealPaths::test_kill_switch_disabled` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunTyRealPaths::test_success_parses_ty_output` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunTyRealPaths::test_extra_search_path_added_when_src_dir_exists` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunTyRealPaths::test_ty_toml_extra_paths_are_appended` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunTyRealPaths::test_malformed_ty_toml_is_silently_ignored` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunTyRealPaths::test_missing_binary_is_typed_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunTyRealPaths::test_kill_switch_disabled` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunTyRealPaths::test_file_root_scans_parent_dir` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestBuildImportGraphAndCycleRealPaths::test_no_files_produces_empty_graph` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestBuildImportGraphAndCycleRealPaths::test_local_import_adds_edge` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestBuildImportGraphAndCycleRealPaths::test_excluded_dirs_are_skipped` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestBuildImportGraphAndCycleRealPaths::test_run_cycle_no_cycles_is_clean_pass` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestBuildImportGraphAndCycleRealPaths::test_run_cycle_mutual_import_detected` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunBindRealPaths::test_no_bind_markers_is_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunBindRealPaths::test_has_bind_markers_true_when_present` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunBindRealPaths::test_has_bind_markers_false_when_absent` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunBindRealPaths::test_has_bind_markers_survives_unreadable_file` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunBindRealPaths::test_import_error_for_missing_bind_module_is_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunBindRealPaths::test_bind_mismatch_diagnostics_maps_mismatches` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestExportsRealPaths::test_missing_exports_flags_unexported_symbols` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestExportsRealPaths::test_missing_exports_empty_when_all_present` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestExportsRealPaths::test_exports_for_package_no_siblings_is_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestExportsRealPaths::test_exports_for_package_tests_dir_is_exempt` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestExportsRealPaths::test_exports_for_package_reports_missing_symbol` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestExportsRealPaths::test_unexported_symbols_result_builds_note_diagnostics` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestExportsRealPaths::test_run_exports_scans_every_init_file` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestExportsRealPaths::test_run_exports_no_init_files_is_empty` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunCargoRealPaths::test_success_parses_cargo_json` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunCargoRealPaths::test_kill_switch_disabled` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunCargoRealPaths::test_unexpected_crash_is_typed_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunCargoFmtCheckRealPaths::test_all_formatted_is_clean_pass` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunCargoFmtCheckRealPaths::test_unformatted_lines_produce_warning_diagnostics` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunCargoFmtCheckRealPaths::test_kill_switch_disabled` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunCargoTestRealPaths::test_success_parses_cargo_json` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunCargoTestRealPaths::test_kill_switch_disabled` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunCargoTestRealPaths::test_unexpected_crash_is_typed_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestCmakeConfigureRealPaths::test_success_returns_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestCmakeConfigureRealPaths::test_nonzero_exit_returns_typed_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestCmakeConfigureRealPaths::test_missing_binary_is_typed_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestCmakeConfigureRealPaths::test_unexpected_crash_is_typed_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestCmakeConfigureRealPaths::test_kill_switch_disabled` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunCmakeBuildRealPaths::test_configure_failure_short_circuits` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunCmakeBuildRealPaths::test_build_success_reports_build_succeeded` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunCmakeBuildRealPaths::test_missing_binary_is_typed_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunCmakeBuildRealPaths::test_unexpected_crash_is_typed_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunCmakeBuildRealPaths::test_kill_switch_disabled` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunClangTidyCmakeRealPaths::test_no_compile_commands_is_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunClangTidyCmakeRealPaths::test_no_sources_is_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunClangTidyCmakeRealPaths::test_success_parses_clang_tidy_output` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunClangTidyCmakeRealPaths::test_missing_binary_is_typed_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunClangTidyCmakeRealPaths::test_kill_switch_disabled` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunClangTidyCmakeRealPaths::test_parse_failure_is_typed_crash_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunClangFormatRealPaths::test_no_sources_is_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunClangFormatRealPaths::test_all_formatted_is_clean_pass` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunClangFormatRealPaths::test_needs_format_produces_diagnostics` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunClangFormatRealPaths::test_missing_binary_is_typed_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunClangFormatRealPaths::test_kill_switch_disabled` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunCtestRealPaths::test_missing_build_dir_is_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunCtestRealPaths::test_success_parses_junit_report` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunCtestRealPaths::test_falls_back_to_text_parsing_without_junit` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunCtestRealPaths::test_malformed_junit_is_typed_crash_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunCtestRealPaths::test_missing_binary_is_typed_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunCtestRealPaths::test_unexpected_crash_is_typed_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunCtestRealPaths::test_kill_switch_disabled` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestFindTestBinaryFromCargoJson::test_finds_test_executable` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestFindTestBinaryFromCargoJson::test_ignores_non_test_artifacts` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestFindTestBinaryFromCargoJson::test_skips_malformed_json_lines` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestFindTestBinaryFromCargoJson::test_no_matching_message_is_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunCargoValgrindRealPaths::test_no_test_binary_found_is_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunCargoValgrindRealPaths::test_missing_cargo_binary_is_typed_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunCargoValgrindRealPaths::test_build_kill_switch_disabled` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunCargoValgrindRealPaths::test_valgrind_success_parses_output` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunCargoValgrindRealPaths::test_missing_valgrind_binary_is_typed_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_native_cargo_runners.py::TestRunCargoValgrindRealPaths::test_run_kill_switch_disabled` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 140 passed (from 140 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
