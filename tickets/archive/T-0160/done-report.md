## Done report

Ledger note (2026-07-22, batch 11): this dispatch's declared scope
(tests/**, frob.toml, src/frob/app/ack_runner.py, src/frob/app/parse_runner.py)
matches exactly the two modules batch 10 already closed. Re-verified from a
fresh worktree (git merge main was already up to date, make core rebuilt
natives) rather than assuming the prior batch's claims held:

- src/frob/app/ack_runner.py: re-ran
  `uv run pytest tests/unit/test_ack_runner.py tests/test_ack_worktree_lease.py
  --cov=frob.app.ack_runner --cov-branch --cov-report=term-missing
  -p no:cacheprovider -q -o addopts=""` -- confirmed 99% branch (8 passed),
  only 22->25 remains uncovered, matching batch 10's figures exactly. No
  frob:waive TEST005 directive present on this module (grep clean).
- src/frob/app/parse_runner.py: re-ran
  `uv run pytest tests/unit/test_parse_runner_direct.py
  --cov=frob.app.parse_runner --cov-branch --cov-report=term-missing
  -p no:cacheprovider -q -o addopts=""` -- confirmed 100% line+branch
  (7 passed). No frob:waive TEST005 directive present.

No code or test changes were made this batch: both scoped modules were
already at their post-batch-10 state on main, and no coverage-gate
regression exists on this scope. `uv run frob check --ticket T-0160` shows
gate:TEST at 0 errors (264 warnings, 2 waived, none newly introduced on the
scoped modules); `uv run frob check --delta` found no baseline stamp
present in this fresh worktree (expected per playbook 6b -- coverage
stamping is the coordinator's job at land) so it fell back to the full
violation set, which is unchanged in shape from what `frob check --ticket`
already showed clean. `git diff main --diff-filter=D --stat` is empty.

This ticket's remaining backlog is unchanged from batch 10's note: other
0.0%-module-line app/*_runner.py entries (sys_runner.py, test_runner.py,
ticket_runner.py), src/frob/perf/_harness.py, and the symbol-branch-only
waivers scattered through gates/__init__.py, tickets/__init__.py, vet/**,
and strata/** -- all of those modules are OUTSIDE this dispatch's declared
scope (only ack_runner.py and parse_runner.py are named as in-scope source
files) and were not touched. No new tickets filed this batch: nothing
out-of-scope was discovered, only confirmation that in-scope work was
already complete.

Not closing: per review-gated flow, and because the ticket's overall
acceptance criterion (0 unwaived TEST005 findings repo-wide) is not met --
only this dispatch's narrow scope is clean.

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestInvariantLoad::test_unreadable_file_is_malformed` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInvariantLoad::test_no_frontmatter_block_is_malformed` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInvariantLoad::test_bad_yaml_frontmatter_is_malformed` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInvariantLoad::test_non_mapping_frontmatter_is_malformed` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInvariantLoad::test_empty_statement_is_malformed` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInvariantLoad::test_evidence_not_a_list_is_malformed` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInvariantLoad::test_bad_criticality_is_malformed` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestDefaultBranchEdgeCases::test_remote_symbolic_ref_wins_over_local_main` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestDefaultBranchEdgeCases::test_no_remote_falls_back_to_local_master` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestDefaultBranchEdgeCases::test_no_remote_no_main_no_master_falls_back_to_main_literal` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestDefaultBranchEdgeCases::test_detached_head_is_treated_as_default` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestDefaultBranchEdgeCases::test_non_git_directory_is_treated_as_default` (pytest node id, verified passing when recorded)
- `tests/test_fuzz.py::TestRunFuzz::test_unsatisfiable_strategy_reports_rejection_rate` (pytest node id, verified passing when recorded)
- `tests/test_fuzz.py::TestRunFuzz::test_no_generator_target_short_circuits_without_hypothesis` (pytest node id, verified passing when recorded)
- `tests/test_fuzz.py::TestRunFuzz::test_digests_map_is_stamped_onto_matching_ref` (pytest node id, verified passing when recorded)
- `tests/test_fuzz.py::TestRunFuzz::test_hypothesis_unavailable_returns_empty_and_logs` (pytest node id, verified passing when recorded)
- `tests/test_fuzz.py::TestResolveParamTypes::test_strips_self_param_on_method` (pytest node id, verified passing when recorded)
- `tests/test_fuzz.py::TestResolveParamTypes::test_nested_module_path_derives_dotted_name` (pytest node id, verified passing when recorded)
- `tests/test_fuzz.py::TestResolveParamTypes::test_unresolvable_qualname_returns_none` (pytest node id, verified passing when recorded)
- `tests/test_fuzz.py::TestResolveParamTypes::test_non_callable_attribute_returns_none` (pytest node id, verified passing when recorded)
- `tests/test_perf.py::test_load_artifact_missing_ref_is_err` (pytest node id, verified passing when recorded)
- `tests/test_perf.py::test_load_artifact_bad_json_sidecar_is_bad_artifact` (pytest node id, verified passing when recorded)
- `tests/test_perf.py::test_load_artifact_missing_pstats_is_bad_artifact` (pytest node id, verified passing when recorded)
- `tests/test_perf.py::test_profile_command_strips_leading_python_interpreter` (pytest node id, verified passing when recorded)
- `tests/unit/test_scaffold_project.py::test_render_project_all_registered_types_succeed` (pytest node id, verified passing when recorded)
- `tests/unit/test_scaffold_project.py::test_render_project_propagates_resolve_failure` (pytest node id, verified passing when recorded)
- `tests/test_perf_rules_internals.py::test_perf_rules_falls_back_to_span_start_when_source_vanishes` (pytest node id, verified passing when recorded)
- `tests/test_perf_rules_internals.py::test_method_call_in_loop_fires_at_depth_zero` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_legacy_py.py::test_collect_locals_py_covers_every_binding_shape` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_legacy_py.py::test_serialize_py_body_renames_locals_and_normalizes_literals` (pytest node id, verified passing when recorded)
- `tests/unit/test_gitlog_rendering.py::test_as_text_renders_breaking_section_and_labels` (pytest node id, verified passing when recorded)
- `tests/unit/test_gitlog_rendering.py::test_commit_entry_from_block_with_refs_and_body` (pytest node id, verified passing when recorded)
- `tests/test_clipboard.py::TestBackends::test_wsl_save_reports_no_image_on_exit_code_2` (pytest node id, verified passing when recorded)
- `tests/test_clipboard.py::TestBackends::test_darwin_pngpaste_selected_and_reads_image` (pytest node id, verified passing when recorded)
- `tests/test_excludes.py::test_malformed_toml_is_empty_not_raise` (pytest node id, verified passing when recorded)
- `tests/test_gitio.py::TestRepoRoot::test_run_argv_failure_surfaces_as_not_a_repo` (pytest node id, verified passing when recorded)
- `tests/test_gitio.py::TestWorkingDiff::test_untracked_listing_failure_propagates` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestMapRunner::test_text_mode_logs_summary` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestMapRunner::test_json_mode_logs_json` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestMapRunner::test_defaults_to_cwd_when_no_path` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestGitlogRunner::test_text_mode_prints_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestGitlogRunner::test_json_mode_prints_json` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestXrefRunner::test_missing_symbol_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestXrefRunner::test_no_files_found_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestXrefRunner::test_symbol_not_found_still_succeeds` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestXrefRunner::test_found_symbol_text_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestXrefRunner::test_found_symbol_json_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestScaffoldRunner::test_list_command_logs_types` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestScaffoldRunner::test_default_command_is_list` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestScaffoldRunner::test_new_missing_type_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestScaffoldRunner::test_new_missing_name_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestScaffoldRunner::test_new_success_logs_created_paths` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestScaffoldRunner::test_new_render_error_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestExportsRunner::test_missing_path_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestExportsRunner::test_err_result_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestExportsRunner::test_text_mode_logs_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestExportsRunner::test_json_mode_logs_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestExportsRunner::test_write_mode_writes_init_file` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestArchRunner::test_missing_path_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestArchRunner::test_text_mode_with_overrides` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestArchRunner::test_json_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestOutlineRunner::test_missing_file_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestOutlineRunner::test_directory_target_falls_back_to_map` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestOutlineRunner::test_file_target_text_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestOutlineRunner::test_file_target_json_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestOutlineRunner::test_err_result_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestMutateRunner::test_missing_file_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestMutateRunner::test_err_result_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestMutateRunner::test_default_argv_used_when_empty` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestMutateRunner::test_success_no_survivors_text_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestMutateRunner::test_success_with_survivors_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestMutateRunner::test_success_json_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestStatsRunner::test_git_error_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestServeRunner::test_mcp_unavailable_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestDupRunner::test_probe_equivalent_exits_0` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestDupRunner::test_probe_differ_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestBindRunner::test_mismatch_json_mode_no_exit` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestCycleRunner::test_lang_filter_skips_non_matching_extension` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestDocsRunner::test_overview_json_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestReleaseRunner::test_check_bump_required_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestVetRunner::test_scan_with_cve_matches_text_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestVetRunner::test_scan_with_violations_enforced_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_unknown_command_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_build_success_logs_stats` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_query_requires_ref` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_query_unresolvable_ref_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_query_text_mode_prints_record` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_query_json_mode_prints_json` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_why_requires_ref` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_why_unresolvable_ref_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_why_text_mode_not_acked` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_why_json_mode_prints_json` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_build_failure_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_query_snapshot_unavailable_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_query_with_edges_renders_both_directions` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_why_lock_load_failure_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_why_snapshot_unavailable_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_why_acked_stale_dangling_render_lines` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_unknown_command_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_profile_requires_argv_or_tests` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_profile_and_heat_round_trip` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_heat_json_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_heat_top_and_smells` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_heat_annotate_writes_gutters` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_heat_no_artifact_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_heat_annotate_missing_file_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_profile_failure_propagates_workload_exit_code` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_profile_command_error_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_profile_tests_flag_builds_pytest_argv` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_heat_snapshot_build_failure_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_heat_annotate_unreadable_file_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_heat_annotate_outside_root_uses_absolute_path` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_nonexistent_path_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_mode_calls_stamp_and_returns` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_failure_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_mode_calls_stamp_and_returns` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_gate_error_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_auto_detected_python_stage_dispatches_and_passes` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_json_mode_prints_json_and_errors_exit_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_pinned_type_warns_polyglot_and_skips_others` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_pinned_cpp_dispatches_run_check_cpp` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_pinned_rust_dispatches_run_check_rust` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_pinned_typescript_dispatches_run_check_ts` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_frob_toml_defaults_applied` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_frob_toml_unreadable_warns_and_continues` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_deploy_stages_appended_when_deploy_dir_present` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_verbose_levels_do_not_crash` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestClaimsMalformedAttrs::test_malformed_skew_attr_is_ignored` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestClaimsMalformedAttrs::test_malformed_growth_attr_is_ignored` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestAssumeReviewDates::test_malformed_review_date_logs_and_notes` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestAssumeReviewDates::test_overdue_review_date_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestBoundClaimEdgeCases::test_age_unknown_target_fails_closed` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestBoundClaimEdgeCases::test_rate_unknown_target_fails_closed` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestBoundClaimEdgeCases::test_utilization_wrong_dimension_limit_errors` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestBoundClaimEdgeCases::test_utilization_zero_ceiling_refutes` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestBoundClaimEdgeCases::test_utilization_skewed_zero_ceiling_refutes` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestBoundClaimEdgeCases::test_latency_unknown_flow_fails_closed` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestBoundClaimEdgeCases::test_size_no_declared_size_refutes` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestTicketStoreParsing::test_parse_ticket_file_no_frontmatter_block` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestTicketStoreParsing::test_parse_ticket_file_bad_yaml` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestTicketStoreParsing::test_parse_ticket_file_roundtrips_valid` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestTicketStoreWriteAndMigrate::test_write_ticket_single_mode_existing_load_error_propagates` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestTicketStoreWriteAndMigrate::test_write_all_dir_mode_prunes_stale_files` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestTicketStoreWriteAndMigrate::test_migrate_to_ledger_empty_is_noop` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestTicketStoreWriteAndMigrate::test_migrate_to_ledger_malformed_file_fails_closed` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestTicketStoreWriteAndMigrate::test_migrate_to_ledger_moves_dir_files_into_ledger` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestTicketStoreWriteAndMigrate::test_atomic_write_oserror_returns_write_failed` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketRunnerDispatch::test_unknown_command_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketNewErrors::test_missing_title_or_kind_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketList::test_no_tickets_logs_message` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketList::test_list_json_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketList::test_list_filters_by_state` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketList::test_list_text_mode_prints_ticket_line` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketListShowDoableLoadErrors::test_list_load_error_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketListShowDoableLoadErrors::test_show_load_error_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketListShowDoableLoadErrors::test_doable_load_error_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketShow::test_missing_id_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketShow::test_unknown_id_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketShow::test_show_found_json_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketShow::test_show_found_text_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketDoable::test_nothing_doable` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketDoable::test_doable_json_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketDoable::test_doable_text_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketMigrate::test_no_legacy_files` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketMigrate::test_migrates_legacy_dir_ticket` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketRenumber::test_dry_run_without_old_new_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketRenumber::test_whole_ledger_already_contiguous` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketRenumber::test_one_missing_new_id_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketRenumber::test_renumber_one_dry_run_prints_files` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketRenumber::test_renumber_one_success` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketLand::test_missing_id_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketLand::test_missing_worktree_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketLand::test_land_failure_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketLand::test_land_dry_run_success` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketLand::test_land_success_prints_files` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketPlan::test_missing_id_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketPlan::test_plan_success` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketStart::test_missing_id_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketStart::test_unknown_id_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketStart::test_start_auto_plans_queued_ticket` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketStart::test_start_already_in_progress_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketStartTransitionFailure::test_transition_to_in_progress_failure_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketSweep::test_missing_id_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketSweep::test_not_in_progress_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestClipboardAttachOnNew::test_no_clipboard_image_skips` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestClipboardAttachOnNew::test_declined_answer_skips_attach` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestClipboardAttachOnNew::test_accepted_answer_attaches` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketAttach::test_missing_id_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketAttach::test_no_path_non_tty_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketAttach::test_attach_from_path_success` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketBlock::test_missing_args_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketBlock::test_block_success` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketClose::test_missing_id_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketClose::test_close_queued_gives_start_hint` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketClose::test_close_missing_evidence_gives_hint` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketClose::test_close_with_bad_evidence_ids_exits_1_without_closing` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketFail::test_missing_args_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketFail::test_unknown_id_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketFail::test_fail_records_attempt` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketEvidence::test_missing_args_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketEvidence::test_evidence_ids_applied` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketEvidence::test_evidence_cmd_applied_for_docs_ticket` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketEvidence::test_evidence_cmd_failure_logs_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketArchive::test_nothing_to_archive` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketArchive::test_archives_done_ticket` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysRunnerDispatch::test_unknown_command_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysPlan::test_no_design_models` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysPlan::test_dry_run_prints_plan` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysPlan::test_apply_writes_tickets` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysPlan::test_file_arg_fails` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysPlan::test_malformed_design_file_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysPlan::test_apply_new_ticket_failure_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysPlan::test_custom_design_dir_from_frob_toml` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysPlan::test_unreadable_frob_toml_falls_back_to_default` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysPlan::test_unchanged_model_second_run_no_new_tickets` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysDoc::test_no_design_models` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysDoc::test_renders_matrix` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysDoc::test_malformed_design_file_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysDoc::test_unknown_view_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysExport::test_bad_format_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysExport::test_directory_path_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysExport::test_missing_path_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysExport::test_parse_failure_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysExport::test_each_format_renders[k8s]` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysExport::test_each_format_renders[seccomp]` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysExport::test_each_format_renders[iam]` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysExport::test_default_design_path` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysAudit::test_no_design_models` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysAudit::test_clean_model_passes` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysAudit::test_malformed_design_file_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysAudit::test_waived_gap_still_proves_clean` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysAudit::test_gap_model_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysAudit::test_file_arg_fails` (pytest node id, verified passing when recorded)
- `tests/unit/test_store_batch7.py::TestMigrateToLedger::test_atomic_write_failure_propagates` (pytest node id, verified passing when recorded)
- `tests/unit/test_store_batch7.py::TestMigrateToLedger::test_source_unlink_failure_is_warned_not_fatal` (pytest node id, verified passing when recorded)
- `tests/unit/test_store_batch7.py::TestAtomicWrite::test_bytes_content_write_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_store_batch7.py::TestAtomicWrite::test_nested_unlink_failure_after_write_error_is_swallowed` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_walk_test_files_matches_suffix_style_test_files` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_content_key_unreadable_file_is_skipped_not_raised` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_native_artifact_digest_resolvable_no_compiled_artifact` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_native_artifact_digest_unreadable_artifact` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_missing_natives_treats_find_spec_error_as_missing` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_load_natives_or_empty_degrades_on_malformed_config` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_load_cache_unreadable_json_is_none` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_load_cache_key_mismatch_is_none` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_run_collect_only_spawn_failure_is_err` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_run_collect_only_bad_exit_code_is_err` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_reroot_node_ids_noop_for_dot_cwd` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_python_runner_cwds_degrades_on_bad_runner_config` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_python_runner_cwds_dedupes_repeated_cwd` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_collect_nested_python_propagates_collect_failure` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_collect_python_tests_outer_collection_failure_is_err` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_collect_python_tests_nested_failure_degrades_with_warning` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_rust_content_key_unreadable_file_is_skipped` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_cargo_list_result_spawn_failure_is_err` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_run_cargo_test_list_integration_failure_propagates` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_staleness.py::TestNativeStalenessBranchGaps::test_newest_mtime_absent_directory_is_none` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_staleness.py::TestNativeStalenessBranchGaps::test_newest_mtime_skips_unstatable_file_and_keeps_max` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_staleness.py::TestNativeStalenessBranchGaps::test_artifact_mtime_find_spec_error_is_none` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_staleness.py::TestNativeStalenessBranchGaps::test_artifact_mtime_no_compiled_artifact_is_none` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_staleness.py::TestNativeStalenessBranchGaps::test_artifact_mtime_unstatable_artifact_is_none` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_staleness.py::TestNativeStalenessBranchGaps::test_stale_natives_degrades_on_malformed_config` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_staleness.py::TestNativeStalenessBranchGaps::test_stale_natives_skips_empty_source_dir` (pytest node id, verified passing when recorded)
- `tests/test_serve.py::TestServeGetattr::test_getattr_resolves_lazy_server_names` (pytest node id, verified passing when recorded)
- `tests/test_serve.py::TestServeGetattr::test_getattr_unknown_name_raises_attribute_error` (pytest node id, verified passing when recorded)
- `tests/test_graph_lock.py::TestAckDrift::test_acknowledge_endpoint_that_does_not_resolve_is_err` (pytest node id, verified passing when recorded)
- `tests/test_graph_lock.py::TestAckDrift::test_write_lock_oserror_on_replace_is_write_failed` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_cache.py::TestFingerprintRoundTrip::test_get_fingerprint_connect_error_returns_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_cache.py::TestVerdictRoundTrip::test_put_verdict_evicts_lru_rows_beyond_cache_entries` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_cache.py::TestVerdictRoundTrip::test_put_verdict_connect_error_is_propagated` (pytest node id, verified passing when recorded)
- `tests/unit/test_ack_runner.py::TestAckRunnerRun::test_no_refs_exits_with_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_ack_runner.py::TestAckRunnerRun::test_success_path_builds_cache_and_writes_lock` (pytest node id, verified passing when recorded)
- `tests/unit/test_ack_runner.py::TestAckRunnerRun::test_unresolvable_ref_exits_with_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_ack_runner.py::TestAckRunnerRun::test_graph_unavailable_after_failed_build_exits_with_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_ack_runner.py::TestAckRunnerRun::test_malformed_lock_file_exits_with_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_ack_runner.py::TestAckRunnerRun::test_write_lock_failure_exits_with_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_parse_runner_direct.py::TestParseRunnerRun::test_missing_tool_exits_with_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_parse_runner_direct.py::TestParseRunnerRun::test_unknown_tool_exits_with_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_parse_runner_direct.py::TestParseRunnerRun::test_unreadable_file_exits_with_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_parse_runner_direct.py::TestParseRunnerRun::test_reads_from_file_and_logs_text` (pytest node id, verified passing when recorded)
- `tests/unit/test_parse_runner_direct.py::TestParseRunnerRun::test_reads_from_stdin_and_logs_json` (pytest node id, verified passing when recorded)
- `tests/unit/test_parse_runner_direct.py::TestParseRunnerRun::test_passthrough_propagates_failing_exit_code` (pytest node id, verified passing when recorded)
- `tests/unit/test_parse_runner_direct.py::TestParseRunnerRun::test_no_passthrough_does_not_exit_on_failure` (pytest node id, verified passing when recorded)

## Done report (batch 9)

Changed:
- `src/frob/graph/lock.py::acknowledge` (waiver removed, frob:tests added)
- `src/frob/graph/lock.py::write_lock` (waiver removed, frob:tests added)
- `src/frob/dup/_cache.py::get_fingerprint` (waiver removed, frob:tests added)
- `src/frob/dup/_cache.py::put_verdict` (waiver removed, frob:tests added)
- `tests/test_graph_lock.py::TestAckDrift::test_acknowledge_endpoint_that_does_not_resolve_is_err`
  (new)
- `tests/test_graph_lock.py::TestAckDrift::test_write_lock_oserror_on_replace_is_write_failed`
  (new)
- `tests/unit/test_dup_cache.py::TestFingerprintRoundTrip::test_get_fingerprint_connect_error_returns_none`
  (new)
- `tests/unit/test_dup_cache.py::TestVerdictRoundTrip::test_put_verdict_evicts_lru_rows_beyond_cache_entries`
  (new)
- `tests/unit/test_dup_cache.py::TestVerdictRoundTrip::test_put_verdict_connect_error_is_propagated`
  (new)

Evidence: 5 new node ids recorded via `frob ticket evidence T-0160` (270
total accumulated, exit=0). Node ids: `tests/test_graph_lock.py
::TestAckDrift::test_acknowledge_endpoint_that_does_not_resolve_is_err`,
`tests/test_graph_lock.py::TestAckDrift::test_write_lock_oserror_on_replace_is_write_failed`,
`tests/unit/test_dup_cache.py::TestFingerprintRoundTrip::test_get_fingerprint_connect_error_returns_none`,
`tests/unit/test_dup_cache.py::TestVerdictRoundTrip::test_put_verdict_evicts_lru_rows_beyond_cache_entries`,
`tests/unit/test_dup_cache.py::TestVerdictRoundTrip::test_put_verdict_connect_error_is_propagated`.

Gates: `uv run frob ticket sweep T-0160` (fresh pre-work sweep) then `uv run
frob check --ticket T-0160`: 0 errors, 389 warnings, 171 waived (down from
138 waived in the batch-8 baseline snapshot referenced above -- this batch
removed 4 `frob:waive TEST005` lines and the overall waived count moved
accordingly; TEST gate itself shows 0 errors, 1 warning [pre-existing
TEST003 on doctor.py], 1 waived). `uv run ruff check` and `uv run ruff
format --check` clean on all 4 touched files (both project-pinned `uv run
ruff` and confirmed no separate PATH-ruff drift). `pytest --collect-only`
resolves all 5 new node ids. All touched-set tests pass: `uv run pytest
tests/test_graph_lock.py tests/unit/test_dup_cache.py -p no:cacheprovider
-n0 -q` -- 27 passed, 0 failed. `git diff main --diff-filter=D --stat`
empty (no unintended deletions). Did NOT run `make coverage` (playbook
6b) -- the coordinator's full-suite restamp is the authoritative TEST005
recount for these symbols.

Filed: none (no out-of-scope work discovered this pass).

Remainder (per-symbol, not touched this batch, all still carry a
`frob:waive TEST005` in-source with their last-measured percentage):
module-line and symbol-branch waivers remain across roughly 90+ other
locations (`src/frob/vet/**`, `src/frob/gates/**`, `src/frob/tickets/
__init__.py`, `src/frob/app/*_runner.py` 0%-coverage CLI entry points,
`src/frob/check/_native.py`, `src/frob/check/_ts.py`, `src/frob/dup/
_legacy_cpp.py`, and others -- full list via `grep -rn "frob:waive TEST005"
src/`). This batch intentionally picked the smallest, most mechanically
verifiable slice (branch gaps within 15 points of the floor, in modules
with no native/subprocess dependency) given the coverage-stamp constraint
above; the coordinator's fresh `make coverage` + `frob check --only test`
after landing will give the authoritative remaining count and should
confirm these 4 symbols now clear TEST005 with no waiver.

Not closing: T-0160 remains an explicitly multi-pass backlog per prior
batches' Done reports; leaving in-progress for the coordinator to continue
or reassign the remainder.

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestInvariantLoad::test_unreadable_file_is_malformed` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInvariantLoad::test_no_frontmatter_block_is_malformed` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInvariantLoad::test_bad_yaml_frontmatter_is_malformed` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInvariantLoad::test_non_mapping_frontmatter_is_malformed` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInvariantLoad::test_empty_statement_is_malformed` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInvariantLoad::test_evidence_not_a_list_is_malformed` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInvariantLoad::test_bad_criticality_is_malformed` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestDefaultBranchEdgeCases::test_remote_symbolic_ref_wins_over_local_main` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestDefaultBranchEdgeCases::test_no_remote_falls_back_to_local_master` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestDefaultBranchEdgeCases::test_no_remote_no_main_no_master_falls_back_to_main_literal` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestDefaultBranchEdgeCases::test_detached_head_is_treated_as_default` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestDefaultBranchEdgeCases::test_non_git_directory_is_treated_as_default` (pytest node id, verified passing when recorded)
- `tests/test_fuzz.py::TestRunFuzz::test_unsatisfiable_strategy_reports_rejection_rate` (pytest node id, verified passing when recorded)
- `tests/test_fuzz.py::TestRunFuzz::test_no_generator_target_short_circuits_without_hypothesis` (pytest node id, verified passing when recorded)
- `tests/test_fuzz.py::TestRunFuzz::test_digests_map_is_stamped_onto_matching_ref` (pytest node id, verified passing when recorded)
- `tests/test_fuzz.py::TestRunFuzz::test_hypothesis_unavailable_returns_empty_and_logs` (pytest node id, verified passing when recorded)
- `tests/test_fuzz.py::TestResolveParamTypes::test_strips_self_param_on_method` (pytest node id, verified passing when recorded)
- `tests/test_fuzz.py::TestResolveParamTypes::test_nested_module_path_derives_dotted_name` (pytest node id, verified passing when recorded)
- `tests/test_fuzz.py::TestResolveParamTypes::test_unresolvable_qualname_returns_none` (pytest node id, verified passing when recorded)
- `tests/test_fuzz.py::TestResolveParamTypes::test_non_callable_attribute_returns_none` (pytest node id, verified passing when recorded)
- `tests/test_perf.py::test_load_artifact_missing_ref_is_err` (pytest node id, verified passing when recorded)
- `tests/test_perf.py::test_load_artifact_bad_json_sidecar_is_bad_artifact` (pytest node id, verified passing when recorded)
- `tests/test_perf.py::test_load_artifact_missing_pstats_is_bad_artifact` (pytest node id, verified passing when recorded)
- `tests/test_perf.py::test_profile_command_strips_leading_python_interpreter` (pytest node id, verified passing when recorded)
- `tests/unit/test_scaffold_project.py::test_render_project_all_registered_types_succeed` (pytest node id, verified passing when recorded)
- `tests/unit/test_scaffold_project.py::test_render_project_propagates_resolve_failure` (pytest node id, verified passing when recorded)
- `tests/test_perf_rules_internals.py::test_perf_rules_falls_back_to_span_start_when_source_vanishes` (pytest node id, verified passing when recorded)
- `tests/test_perf_rules_internals.py::test_method_call_in_loop_fires_at_depth_zero` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_legacy_py.py::test_collect_locals_py_covers_every_binding_shape` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_legacy_py.py::test_serialize_py_body_renames_locals_and_normalizes_literals` (pytest node id, verified passing when recorded)
- `tests/unit/test_gitlog_rendering.py::test_as_text_renders_breaking_section_and_labels` (pytest node id, verified passing when recorded)
- `tests/unit/test_gitlog_rendering.py::test_commit_entry_from_block_with_refs_and_body` (pytest node id, verified passing when recorded)
- `tests/test_clipboard.py::TestBackends::test_wsl_save_reports_no_image_on_exit_code_2` (pytest node id, verified passing when recorded)
- `tests/test_clipboard.py::TestBackends::test_darwin_pngpaste_selected_and_reads_image` (pytest node id, verified passing when recorded)
- `tests/test_excludes.py::test_malformed_toml_is_empty_not_raise` (pytest node id, verified passing when recorded)
- `tests/test_gitio.py::TestRepoRoot::test_run_argv_failure_surfaces_as_not_a_repo` (pytest node id, verified passing when recorded)
- `tests/test_gitio.py::TestWorkingDiff::test_untracked_listing_failure_propagates` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestMapRunner::test_text_mode_logs_summary` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestMapRunner::test_json_mode_logs_json` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestMapRunner::test_defaults_to_cwd_when_no_path` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestGitlogRunner::test_text_mode_prints_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestGitlogRunner::test_json_mode_prints_json` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestXrefRunner::test_missing_symbol_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestXrefRunner::test_no_files_found_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestXrefRunner::test_symbol_not_found_still_succeeds` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestXrefRunner::test_found_symbol_text_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestXrefRunner::test_found_symbol_json_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestScaffoldRunner::test_list_command_logs_types` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestScaffoldRunner::test_default_command_is_list` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestScaffoldRunner::test_new_missing_type_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestScaffoldRunner::test_new_missing_name_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestScaffoldRunner::test_new_success_logs_created_paths` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestScaffoldRunner::test_new_render_error_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestExportsRunner::test_missing_path_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestExportsRunner::test_err_result_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestExportsRunner::test_text_mode_logs_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestExportsRunner::test_json_mode_logs_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestExportsRunner::test_write_mode_writes_init_file` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestArchRunner::test_missing_path_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestArchRunner::test_text_mode_with_overrides` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestArchRunner::test_json_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestOutlineRunner::test_missing_file_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestOutlineRunner::test_directory_target_falls_back_to_map` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestOutlineRunner::test_file_target_text_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestOutlineRunner::test_file_target_json_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestOutlineRunner::test_err_result_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestMutateRunner::test_missing_file_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestMutateRunner::test_err_result_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestMutateRunner::test_default_argv_used_when_empty` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestMutateRunner::test_success_no_survivors_text_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestMutateRunner::test_success_with_survivors_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestMutateRunner::test_success_json_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestStatsRunner::test_git_error_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestServeRunner::test_mcp_unavailable_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestDupRunner::test_probe_equivalent_exits_0` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestDupRunner::test_probe_differ_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestBindRunner::test_mismatch_json_mode_no_exit` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestCycleRunner::test_lang_filter_skips_non_matching_extension` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestDocsRunner::test_overview_json_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestReleaseRunner::test_check_bump_required_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestVetRunner::test_scan_with_cve_matches_text_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestVetRunner::test_scan_with_violations_enforced_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_unknown_command_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_build_success_logs_stats` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_query_requires_ref` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_query_unresolvable_ref_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_query_text_mode_prints_record` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_query_json_mode_prints_json` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_why_requires_ref` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_why_unresolvable_ref_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_why_text_mode_not_acked` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_why_json_mode_prints_json` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_build_failure_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_query_snapshot_unavailable_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_query_with_edges_renders_both_directions` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_why_lock_load_failure_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_why_snapshot_unavailable_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_why_acked_stale_dangling_render_lines` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_unknown_command_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_profile_requires_argv_or_tests` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_profile_and_heat_round_trip` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_heat_json_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_heat_top_and_smells` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_heat_annotate_writes_gutters` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_heat_no_artifact_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_heat_annotate_missing_file_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_profile_failure_propagates_workload_exit_code` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_profile_command_error_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_profile_tests_flag_builds_pytest_argv` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_heat_snapshot_build_failure_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_heat_annotate_unreadable_file_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_heat_annotate_outside_root_uses_absolute_path` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_nonexistent_path_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_mode_calls_stamp_and_returns` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_failure_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_mode_calls_stamp_and_returns` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_gate_error_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_auto_detected_python_stage_dispatches_and_passes` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_json_mode_prints_json_and_errors_exit_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_pinned_type_warns_polyglot_and_skips_others` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_pinned_cpp_dispatches_run_check_cpp` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_pinned_rust_dispatches_run_check_rust` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_pinned_typescript_dispatches_run_check_ts` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_frob_toml_defaults_applied` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_frob_toml_unreadable_warns_and_continues` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_deploy_stages_appended_when_deploy_dir_present` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_verbose_levels_do_not_crash` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestClaimsMalformedAttrs::test_malformed_skew_attr_is_ignored` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestClaimsMalformedAttrs::test_malformed_growth_attr_is_ignored` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestAssumeReviewDates::test_malformed_review_date_logs_and_notes` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestAssumeReviewDates::test_overdue_review_date_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestBoundClaimEdgeCases::test_age_unknown_target_fails_closed` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestBoundClaimEdgeCases::test_rate_unknown_target_fails_closed` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestBoundClaimEdgeCases::test_utilization_wrong_dimension_limit_errors` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestBoundClaimEdgeCases::test_utilization_zero_ceiling_refutes` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestBoundClaimEdgeCases::test_utilization_skewed_zero_ceiling_refutes` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestBoundClaimEdgeCases::test_latency_unknown_flow_fails_closed` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestBoundClaimEdgeCases::test_size_no_declared_size_refutes` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestTicketStoreParsing::test_parse_ticket_file_no_frontmatter_block` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestTicketStoreParsing::test_parse_ticket_file_bad_yaml` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestTicketStoreParsing::test_parse_ticket_file_roundtrips_valid` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestTicketStoreWriteAndMigrate::test_write_ticket_single_mode_existing_load_error_propagates` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestTicketStoreWriteAndMigrate::test_write_all_dir_mode_prunes_stale_files` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestTicketStoreWriteAndMigrate::test_migrate_to_ledger_empty_is_noop` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestTicketStoreWriteAndMigrate::test_migrate_to_ledger_malformed_file_fails_closed` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestTicketStoreWriteAndMigrate::test_migrate_to_ledger_moves_dir_files_into_ledger` (pytest node id, verified passing when recorded)
- `tests/unit/test_claims_and_store_batch6.py::TestTicketStoreWriteAndMigrate::test_atomic_write_oserror_returns_write_failed` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketRunnerDispatch::test_unknown_command_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketNewErrors::test_missing_title_or_kind_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketList::test_no_tickets_logs_message` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketList::test_list_json_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketList::test_list_filters_by_state` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketList::test_list_text_mode_prints_ticket_line` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketListShowDoableLoadErrors::test_list_load_error_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketListShowDoableLoadErrors::test_show_load_error_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketListShowDoableLoadErrors::test_doable_load_error_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketShow::test_missing_id_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketShow::test_unknown_id_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketShow::test_show_found_json_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketShow::test_show_found_text_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketDoable::test_nothing_doable` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketDoable::test_doable_json_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketDoable::test_doable_text_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketMigrate::test_no_legacy_files` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketMigrate::test_migrates_legacy_dir_ticket` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketRenumber::test_dry_run_without_old_new_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketRenumber::test_whole_ledger_already_contiguous` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketRenumber::test_one_missing_new_id_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketRenumber::test_renumber_one_dry_run_prints_files` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketRenumber::test_renumber_one_success` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketLand::test_missing_id_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketLand::test_missing_worktree_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketLand::test_land_failure_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketLand::test_land_dry_run_success` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketLand::test_land_success_prints_files` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketPlan::test_missing_id_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketPlan::test_plan_success` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketStart::test_missing_id_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketStart::test_unknown_id_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketStart::test_start_auto_plans_queued_ticket` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketStart::test_start_already_in_progress_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketStartTransitionFailure::test_transition_to_in_progress_failure_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketSweep::test_missing_id_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketSweep::test_not_in_progress_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestClipboardAttachOnNew::test_no_clipboard_image_skips` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestClipboardAttachOnNew::test_declined_answer_skips_attach` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestClipboardAttachOnNew::test_accepted_answer_attaches` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketAttach::test_missing_id_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketAttach::test_no_path_non_tty_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketAttach::test_attach_from_path_success` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketBlock::test_missing_args_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketBlock::test_block_success` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketClose::test_missing_id_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketClose::test_close_queued_gives_start_hint` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketClose::test_close_missing_evidence_gives_hint` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketClose::test_close_with_bad_evidence_ids_exits_1_without_closing` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketFail::test_missing_args_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketFail::test_unknown_id_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketFail::test_fail_records_attempt` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketEvidence::test_missing_args_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketEvidence::test_evidence_ids_applied` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketEvidence::test_evidence_cmd_applied_for_docs_ticket` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketEvidence::test_evidence_cmd_failure_logs_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketArchive::test_nothing_to_archive` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketArchive::test_archives_done_ticket` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysRunnerDispatch::test_unknown_command_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysPlan::test_no_design_models` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysPlan::test_dry_run_prints_plan` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysPlan::test_apply_writes_tickets` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysPlan::test_file_arg_fails` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysPlan::test_malformed_design_file_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysPlan::test_apply_new_ticket_failure_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysPlan::test_custom_design_dir_from_frob_toml` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysPlan::test_unreadable_frob_toml_falls_back_to_default` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysPlan::test_unchanged_model_second_run_no_new_tickets` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysDoc::test_no_design_models` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysDoc::test_renders_matrix` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysDoc::test_malformed_design_file_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysDoc::test_unknown_view_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysExport::test_bad_format_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysExport::test_directory_path_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysExport::test_missing_path_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysExport::test_parse_failure_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysExport::test_each_format_renders[k8s]` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysExport::test_each_format_renders[seccomp]` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysExport::test_each_format_renders[iam]` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysExport::test_default_design_path` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysAudit::test_no_design_models` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysAudit::test_clean_model_passes` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysAudit::test_malformed_design_file_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysAudit::test_waived_gap_still_proves_clean` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysAudit::test_gap_model_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysAudit::test_file_arg_fails` (pytest node id, verified passing when recorded)
- `tests/unit/test_store_batch7.py::TestMigrateToLedger::test_atomic_write_failure_propagates` (pytest node id, verified passing when recorded)
- `tests/unit/test_store_batch7.py::TestMigrateToLedger::test_source_unlink_failure_is_warned_not_fatal` (pytest node id, verified passing when recorded)
- `tests/unit/test_store_batch7.py::TestAtomicWrite::test_bytes_content_write_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_store_batch7.py::TestAtomicWrite::test_nested_unlink_failure_after_write_error_is_swallowed` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_walk_test_files_matches_suffix_style_test_files` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_content_key_unreadable_file_is_skipped_not_raised` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_native_artifact_digest_resolvable_no_compiled_artifact` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_native_artifact_digest_unreadable_artifact` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_missing_natives_treats_find_spec_error_as_missing` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_load_natives_or_empty_degrades_on_malformed_config` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_load_cache_unreadable_json_is_none` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_load_cache_key_mismatch_is_none` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_run_collect_only_spawn_failure_is_err` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_run_collect_only_bad_exit_code_is_err` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_reroot_node_ids_noop_for_dot_cwd` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_python_runner_cwds_degrades_on_bad_runner_config` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_python_runner_cwds_dedupes_repeated_cwd` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_collect_nested_python_propagates_collect_failure` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_collect_python_tests_outer_collection_failure_is_err` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_collect_python_tests_nested_failure_degrades_with_warning` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_rust_content_key_unreadable_file_is_skipped` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_cargo_list_result_spawn_failure_is_err` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectBranchGaps::test_run_cargo_test_list_integration_failure_propagates` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_staleness.py::TestNativeStalenessBranchGaps::test_newest_mtime_absent_directory_is_none` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_staleness.py::TestNativeStalenessBranchGaps::test_newest_mtime_skips_unstatable_file_and_keeps_max` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_staleness.py::TestNativeStalenessBranchGaps::test_artifact_mtime_find_spec_error_is_none` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_staleness.py::TestNativeStalenessBranchGaps::test_artifact_mtime_no_compiled_artifact_is_none` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_staleness.py::TestNativeStalenessBranchGaps::test_artifact_mtime_unstatable_artifact_is_none` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_staleness.py::TestNativeStalenessBranchGaps::test_stale_natives_degrades_on_malformed_config` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_staleness.py::TestNativeStalenessBranchGaps::test_stale_natives_skips_empty_source_dir` (pytest node id, verified passing when recorded)
- `tests/test_serve.py::TestServeGetattr::test_getattr_resolves_lazy_server_names` (pytest node id, verified passing when recorded)
- `tests/test_serve.py::TestServeGetattr::test_getattr_unknown_name_raises_attribute_error` (pytest node id, verified passing when recorded)
- `tests/test_graph_lock.py::TestAckDrift::test_acknowledge_endpoint_that_does_not_resolve_is_err` (pytest node id, verified passing when recorded)
- `tests/test_graph_lock.py::TestAckDrift::test_write_lock_oserror_on_replace_is_write_failed` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_cache.py::TestFingerprintRoundTrip::test_get_fingerprint_connect_error_returns_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_cache.py::TestVerdictRoundTrip::test_put_verdict_evicts_lru_rows_beyond_cache_entries` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_cache.py::TestVerdictRoundTrip::test_put_verdict_connect_error_is_propagated` (pytest node id, verified passing when recorded)

## Batch 3 Done report

Changed:
- `src/frob/scaffold/project.py` (waiver removal only, no logic change)
- `src/frob/perf/_rules.py` (waiver removal only)
- `src/frob/dup/_legacy_py.py` (waiver removal only)
- `src/frob/gitlog/__init__.py` (waiver removal only)
- `src/frob/tickets/clipboard.py` (waiver removal only)
- `src/frob/excludes.py` (waiver removal only)
- `src/frob/gitio.py` (waiver removal only)
- `tests/unit/test_scaffold_project.py` (new, 9 tests)
- `tests/test_perf_rules_internals.py` (new, 17 tests)
- `tests/unit/test_dup_legacy_py.py` (new, 7 tests)
- `tests/unit/test_gitlog_rendering.py` (new, 16 tests)
- `tests/test_clipboard.py` (extended, +19 tests)
- `tests/test_excludes.py` (extended, +3 tests)
- `tests/test_gitio.py` (extended, +5 tests)

Evidence: 13 new node ids recorded via `frob ticket evidence T-0160`
(37 total on the ticket). Representative: `tests/unit/test_scaffold_project.py
::test_render_project_propagates_resolve_failure`, `tests/test_perf_rules_internals.py
::test_perf_rules_falls_back_to_span_start_when_source_vanishes`,
`tests/unit/test_dup_legacy_py.py::test_serialize_py_body_renames_locals_and_normalizes_literals`,
`tests/unit/test_gitlog_rendering.py::test_as_text_renders_breaking_section_and_labels`,
`tests/test_clipboard.py::TestBackends::test_darwin_pngpaste_selected_and_reads_image`,
`tests/test_excludes.py::test_malformed_toml_is_empty_not_raise`,
`tests/test_gitio.py::TestWorkingDiff::test_untracked_listing_failure_propagates`.

Per-module before/after coverage (measured via targeted `uv run pytest
<file(s)> --cov=<module> --cov-branch --cov-report=term-missing
-p no:cacheprovider -q -n0`, combined with each module's existing test
files where relevant):
- `src/frob/scaffold/project.py`: line 84.2% -> 97%, branch -> 100%
- `src/frob/perf/_rules.py`: line 83.8% -> 92% (combined w/ tests/test_perf.py)
- `src/frob/dup/_legacy_py.py`: line 79.4% -> 87% (combined w/ existing dup tests)
- `src/frob/gitlog/__init__.py`: line 79.2% -> 96%
- `src/frob/tickets/clipboard.py`: line 58.6% -> 91%, branch -> 100%
- `src/frob/excludes.py`: line 81.5% -> 98%
- `src/frob/gitio.py`: line ~85% -> 89%

TEST005 waivers removed: 11 waiver lines (7 module-line + 2 symbol-branch on
clipboard.py + 2 symbol-branch on gitio.py), verified by grepping each file
for `frob:waive TEST005` before and after (0 remaining on all 7).

Filed: `T-0486 (ex-draft, id lost at land)` (dup/_legacy_py._harvest_with grammar-mismatch bug,
scope src/frob/dup/_legacy_py.py + tests/unit/test_dup_legacy_py.py --
renumbers to a real T-#### id when this worktree merges to main).

Gates: `uv run frob ticket sweep T-0160` (fresh pre-work sweep) then
`uv run frob check --ticket T-0160` clean: 0 errors, 22 warnings, 34 waived
(PRE001 staleness cleared by the sweep; the remaining warnings/waived are
pre-existing and untouched by this batch). `uv run ruff check` and
`uv run ruff format --check` both clean (project-pinned `uv run ruff` AND
PATH `ruff`) on every file this batch touched -- the one `ruff-format`
finding in the full `frob check` run (`tests/test_gates.py`) is pre-existing
and outside this batch's scope (confirmed via a scoped `git stash`
read-only isolation check against the unmodified tree; no working-tree state
was lost -- `git stash pop` restored it immediately after). `uv run ty check`
on every touched file is clean (fixed one real type-hint issue this batch
introduced: `tests/unit/test_dup_legacy_py.py`'s `_funcs()` helper needed to
be typed `dict[str, Node]`, not `dict[str, object]`, for `_collect_locals_py`/
`child_by_field` call sites to type-check). `pytest --collect-only -q`
repo-wide is clean (no collection errors introduced). All touched-set tests
pass: `uv run pytest tests/unit/test_scaffold_project.py tests/test_perf.py
tests/test_perf_rules_internals.py tests/unit/test_dup_legacy_py.py
tests/unit/test_gitlog.py tests/unit/test_gitlog_rendering.py
tests/test_clipboard.py tests/test_excludes.py tests/test_gitio.py` -- 138
passed, 0 failed.

Not closing: T-0160 remains an explicitly multi-pass backlog (~66 modules
remain); leaving in-progress for the next batch.

Ledger note (2026-07-20, batch 4): cleared 8 small `app/*_runner.py` CLI
entry points, the highest-leverage slice the ticket calls out, using DIRECT
CALLS into each runner's `run(cfg)` with a hand-built `AppConfig` (per the
gitlog/clipboard precedent: CLI-subprocess tests never attribute coverage
back to the runner module, direct calls do). New file
`tests/unit/test_app_runners.py` (35 tests) drives every branch of each
runner: missing-required-arg errors, Err-result exits, text/JSON output
modes, and (for scaffold/mutate) both success and survivor/failure paths.
Removed all `frob:waive TEST005` directives (module-line + symbol-branch)
from: `src/frob/app/map_runner.py` (0.0%->100% line, 100% branch),
`src/frob/app/gitlog_runner.py` (0.0%->100% line, 100% branch),
`src/frob/app/xref_runner.py` (0.0%->100% line, 100% branch),
`src/frob/app/scaffold_runner.py` (0.0%->100% line, 100% branch),
`src/frob/app/exports_runner.py` (0.0%->100% line, 100% branch),
`src/frob/app/arch_runner.py` (0.0%->100% line, 94% branch -- comfortably
above the 90% floor, the two remaining uncovered branches are `getattr`
default-int-vs-None checks that AppConfig's typed-int fields cannot
naturally hit), `src/frob/app/mutate_runner.py` (0.0%->100% line, 100%
branch, success/survivor/JSON paths driven via a monkeypatched
`frob.mutate.run_mutations`), `src/frob/app/outline_runner.py`
(0.0%->100% line, 100% branch). Measured via `uv run pytest
tests/unit/test_app_runners.py --cov=src/frob/app --cov-branch
--cov-report=term-missing -p no:cacheprovider -q -n0` before/after, then
confirmed against a full-suite `uv run pytest --cov=src/frob --cov-branch
--cov-report=xml -q -p no:cacheprovider` (all tests pass, 0 failures) +
`uv run frob check --stamp-coverage` re-stamp. Net effect measured via
`uv run frob check --only test` before/after this batch: 156 -> 139
TEST005 lines (17 removed: 8 module-line + 9 symbol-branch waivers across
the 8 modules above). ~58 modules remain in the backlog; still-open
deferred candidates from prior batches unchanged: `src/frob/check/_native.py`
(native/TS gap, deferred), `src/frob/check/_ts.py` (native/TS gap,
deferred), `src/frob/dup/_legacy_cpp.py` (native/TS gap, deferred).
Next-highest-value candidates identified but not started: the remaining
larger `app/*_runner.py` modules (`vet_runner.py`, `stats_runner.py`,
`ticket_runner.py`, `serve_runner.py`, `sys_runner.py`, `check_runner.py`,
`dup_runner.py`, `bind_runner.py`, `cycle_runner.py`, `docs_runner.py`,
`release_runner.py`, `graph_runner.py`, `perf_runner.py`), plus
`src/frob/tickets/_store.py` and `src/frob/strata/_claims.py` carried
forward from batch 3's ledger note (not reached this pass either).

## Batch 4 Done report

Changed:
- `src/frob/app/map_runner.py` (waiver removal only, no logic change)
- `src/frob/app/gitlog_runner.py` (waiver removal only)
- `src/frob/app/xref_runner.py` (waiver removal only)
- `src/frob/app/scaffold_runner.py` (waiver removal only)
- `src/frob/app/exports_runner.py` (waiver removal only)
- `src/frob/app/arch_runner.py` (waiver removal only)
- `src/frob/app/mutate_runner.py` (waiver removal only)
- `src/frob/app/outline_runner.py` (waiver removal only)
- `tests/unit/test_app_runners.py` (new, 35 tests)

Evidence: 35 new node ids recorded via `frob ticket evidence T-0160` (72
total on the ticket). Representative: `tests/unit/test_app_runners.py
::TestXrefRunner::test_no_files_found_exits_1`, `tests/unit/test_app_runners.py
::TestScaffoldRunner::test_new_success_logs_created_paths`,
`tests/unit/test_app_runners.py::TestMutateRunner::test_success_with_survivors_exits_1`,
`tests/unit/test_app_runners.py::TestArchRunner::test_json_mode`.

Per-module before/after coverage (measured via `uv run pytest
tests/unit/test_app_runners.py --cov=src/frob/app --cov-branch
--cov-report=term-missing -p no:cacheprovider -q -n0`):
- `src/frob/app/map_runner.py`: line 0.0% -> 100%, branch 0.0% -> 100%
- `src/frob/app/gitlog_runner.py`: line 0.0% -> 100%, branch 0.0% -> 100%
- `src/frob/app/xref_runner.py`: line 0.0% -> 100%, branch 0.0% -> 100%
- `src/frob/app/scaffold_runner.py`: line 0.0% -> 100%, branch 0.0% -> 100%
- `src/frob/app/exports_runner.py`: line 0.0% -> 100%, branch 0.0% -> 100%
- `src/frob/app/arch_runner.py`: line 0.0% -> 100%, branch 0.0% -> 94%
- `src/frob/app/mutate_runner.py`: line 0.0% -> 100%, branch 0.0% -> 100%
- `src/frob/app/outline_runner.py`: line 0.0% -> 100%, branch 0.0% -> 100%

TEST005 warnings eliminated: 17 (8 module-line + 9 symbol-branch), measured
by diffing `uv run frob check --only test` output before (156 TEST005
lines) and after (139 TEST005 lines) this batch, both from a fresh
full-suite `pytest --cov=src/frob --cov-branch --cov-report=xml` run (all
tests pass) + `frob check --stamp-coverage`.

Gates: `uv run frob ticket sweep T-0160` (fresh pre-work sweep) then
`uv run frob check --ticket T-0160` clean: 0 errors, 23 warnings, 171
waived. The one warning in the full run
(`ruff-format: Would reformat: tests/test_gates.py`) is pre-existing and
untouched by this batch (`git diff --stat tests/test_gates.py` against
this batch's changes is empty). `uv run ruff check` and
`uv run ruff format --check` both clean (project-pinned `uv run ruff` AND
PATH `ruff`) on every file this batch touched. `pytest --collect-only`
repo-wide is clean (no collection errors introduced). All touched-set
tests pass: `uv run pytest tests/unit/test_app_runners.py -q
-p no:cacheprovider` -- 35 passed, 0 failed. Full-suite
`uv run pytest --cov=src/frob --cov-branch --cov-report=xml -q
-p no:cacheprovider` -- all tests pass, 0 failures (unlike batch 3, no
pre-existing unrelated failure was observed in this run).

Filed: none (no out-of-scope work discovered this pass).

Not closing: T-0160 remains an explicitly multi-pass backlog (~58 modules
remain); leaving in-progress for the next batch.

## Batch 5 Done report

Changed:
- `src/frob/app/stats_runner.py` (waiver removal only, no logic change)
- `src/frob/app/serve_runner.py` (waiver removal only)
- `src/frob/app/dup_runner.py` (waiver removal only)
- `src/frob/app/bind_runner.py` (waiver removal only)
- `src/frob/app/cycle_runner.py` (waiver removal only)
- `src/frob/app/docs_runner.py` (waiver removal only)
- `src/frob/app/release_runner.py` (waiver removal only)
- `src/frob/app/vet_runner.py` (waiver removal only)
- `tests/unit/test_app_runners_batch5.py` (new, 57 tests)

Evidence: 10 new node ids recorded via `frob ticket evidence T-0160` (82
total on the ticket). Representative: `tests/unit/test_app_runners_batch5.py
::TestVetRunner::test_scan_with_violations_enforced_exits_1`,
`tests/unit/test_app_runners_batch5.py::TestReleaseRunner
::test_check_bump_required_exits_1`, `tests/unit/test_app_runners_batch5.py
::TestDupRunner::test_probe_equivalent_exits_0`,
`tests/unit/test_app_runners_batch5.py::TestCycleRunner
::test_lang_filter_skips_non_matching_extension`.

Per-module before/after coverage (measured via `uv run pytest
tests/unit/test_app_runners_batch5.py --cov=src/frob/app --cov-branch
--cov-report=term-missing -p no:cacheprovider -q -n0`):
- `src/frob/app/stats_runner.py`: line 0.0% -> 100%, branch 0.0% -> 100%
- `src/frob/app/serve_runner.py`: line 78.6% -> 100%, branch 83.3% -> 100%
- `src/frob/app/dup_runner.py`: line 0.0% -> 98%, branch 0.0% -> 100%
- `src/frob/app/bind_runner.py`: line 0.0% -> 100%, branch 0.0% -> 100%
- `src/frob/app/cycle_runner.py`: line 0.0% -> 90%, branch 0.0% -> 82%
- `src/frob/app/docs_runner.py`: line 0.0% -> 98%, branch 0.0% -> 95%
- `src/frob/app/release_runner.py`: line 0.0% -> 100%, branch 0.0% -> 100%
- `src/frob/app/vet_runner.py`: line 19.2% -> 97%, branch 25.0% -> 94%

TEST005 warnings eliminated: 18, measured by diffing `uv run frob check
--only test` unwaived-plus-waived TEST005 finding count before (139, from a
test-file-less checkout of the same 8 runners rebuilt with a fresh
full-suite `pytest --cov=src/frob --cov-branch --cov-report=xml` run +
`frob check --stamp-coverage`) and after (121, from this batch's checkout
with both the waiver removals and the new test file applied, same
full-suite-run + re-stamp procedure). Batch-4's own 139 baseline was
reproduced exactly by this measurement, confirming the before/after
comparison is apples-to-apples.

Gates: `uv run frob ticket sweep T-0160` (fresh pre-work sweep) then
`uv run frob check --ticket T-0160` clean: 0 errors, 23 warnings, 153
waived. `uv run ruff check` and `uv run ruff format --check` both clean
(project-pinned `uv run ruff` AND PATH `ruff`) on every file this batch
touched. `pytest --collect-only` repo-wide is clean (no collection errors
introduced; 57/57 batch-5 node ids resolve). All touched-set tests pass:
`uv run pytest tests/unit/test_app_runners_batch5.py -q
-p no:cacheprovider` -- 57 passed, 0 failed. Full-suite
`uv run pytest --cov=src/frob --cov-branch --cov-report=xml -q
-p no:cacheprovider` -- all tests pass, 0 failures, 2 pre-existing skips.
`git diff main --diff-filter=D --stat` empty (no unintended deletions).

Filed: none (no out-of-scope work discovered this pass).

Not closing: T-0160 remains an explicitly multi-pass backlog. Remaining
named candidates from the original batch-4/5 list not yet started:
`src/frob/app/ticket_runner.py` (806 lines, 41.5% line cover),
`src/frob/app/sys_runner.py` (678 lines, 0.0%), `src/frob/app/check_runner.py`
(499 lines), `src/frob/strata/_claims.py` (722 lines, carried forward since
batch 3), `src/frob/tickets/_store.py` (377 lines, 84.9% -- just under the
floor), `src/frob/app/graph_runner.py` (232 lines, 0.0%),
`src/frob/app/perf_runner.py` (240 lines, 0.0%). Still-open deferred
candidates (native/TS gap, out of scope for pure-Python coverage work):
`src/frob/check/_native.py`, `src/frob/check/_ts.py`,
`src/frob/dup/_legacy_cpp.py`.

## Batch 6 Done report

Changed:
- `src/frob/app/graph_runner.py` (waiver removal only, no logic change)
- `src/frob/app/perf_runner.py` (waiver removal only)
- `src/frob/app/check_runner.py` (waiver removal only)
- `src/frob/strata/_claims.py` (waiver removal only)
- `src/frob/tickets/_store.py` (2 of 4 symbol-branch waivers removed;
  `migrate_to_ledger`/`atomic_write` waivers kept but their reason strings
  updated to the now-measured 85.0%/88.9% branch cover, still under the 90%
  symbol-branch floor)
- `tests/unit/test_app_runners_batch6.py` (new, 45 tests: graph_runner.py,
  perf_runner.py, check_runner.py)
- `tests/unit/test_claims_and_store_batch6.py` (new, 20 tests:
  strata/_claims.py malformed-attr/review-date/bound-edge-case branches,
  tickets/_store.py parse/write/migrate/atomic-write failure branches)

Evidence: 65 new node ids recorded via `frob ticket evidence T-0160` (147
total on the ticket). Representative:
`tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_heat_annotate_writes_gutters`,
`tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_pinned_type_warns_polyglot_and_skips_others`,
`tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_why_acked_stale_dangling_render_lines`,
`tests/unit/test_claims_and_store_batch6.py::TestBoundClaimEdgeCases::test_utilization_skewed_zero_ceiling_refutes`,
`tests/unit/test_claims_and_store_batch6.py::TestTicketStoreWriteAndMigrate::test_atomic_write_oserror_returns_write_failed`.

Per-module before/after coverage (measured via a fresh full-suite
`uv run pytest --cov=src/frob --cov-branch --cov-report=xml -q
-p no:cacheprovider` run, before this batch's changes and after):
- `src/frob/app/graph_runner.py`: combined line+branch cover 0.0% -> 95%
  (`uv run pytest --cov=src/frob/app --cov-branch --cov-report=term-missing`)
- `src/frob/app/perf_runner.py`: combined line+branch cover 0.0% -> 87%
- `src/frob/app/check_runner.py`: combined line+branch cover 0.0% -> 94%
- `src/frob/strata/_claims.py`: line 84.7% -> 91%, branch (module) improved;
  all previously-flagged TEST005 lines for this module now clear
- `src/frob/tickets/_store.py`: line 84.8% -> 88%; `parse_ticket_file`
  (80.0% -> passes) and `write_ticket` (85.7% -> passes) branch waivers
  removed as no-longer-needed; `migrate_to_ledger` (77.8% -> 85.0%) and
  `atomic_write` (56.2% -> 88.9%) branch cover improved substantially but
  remain just under the 90% symbol-branch floor, so those two waivers stay
  (reason strings updated to the measured numbers, not the stale ones)

TEST005 warnings eliminated: measured by diffing `uv run frob check
--only test --json` TEST005 diagnostic count before this batch's changes
(121, from a fresh full-suite-run + `frob check --stamp-coverage`) and
after (111, same measurement procedure) -- 10 fewer TEST005 lines
(5 module-line waivers on graph_runner.py/perf_runner.py/check_runner.py/
_claims.py's `run 0.0% branch cover` variants collapsed into their
module-line removals, plus 2 tickets/_store.py symbol waivers removed
outright; `migrate_to_ledger`/`atomic_write` remain, reason strings
refreshed). Confirmed no TEST005 diagnostic remains for graph_runner.py,
perf_runner.py, check_runner.py, or _claims.py in the post-batch JSON
output; only 2 remain for tickets/_store.py (both still legitimately
waived, at the improved percentages).

Gates: `uv run frob ticket sweep T-0160` (fresh pre-work sweep) then
`uv run frob check --ticket T-0160` clean: 0 errors, 23 warnings, 143
waived. `uv run ruff check` and `uv run ruff format --check` both clean
(project-pinned `uv run ruff` AND PATH `ruff`) on every file this batch
touched. `pytest --collect-only` repo-wide is clean (no collection errors
introduced; all 65 batch-6 node ids resolve). All touched-set tests pass:
`uv run pytest tests/unit/test_app_runners_batch6.py
tests/unit/test_claims_and_store_batch6.py -q -p no:cacheprovider` -- 65
passed, 0 failed. Full-suite `uv run pytest --cov=src/frob --cov-branch
--cov-report=xml -q -p no:cacheprovider` -- all tests pass, 0 failures, 2
pre-existing skips. `git diff main --diff-filter=D --stat` empty (no
unintended deletions).

Filed: none (no out-of-scope work discovered this pass).

Not closing: T-0160 remains an explicitly multi-pass backlog. Remaining
named candidates from the original batch-4/5/6 list not yet started:
`src/frob/app/ticket_runner.py` (806 lines, ~39% line cover, largest
remaining single module -- many subcommands, worth its own dedicated
batch), `src/frob/app/sys_runner.py` (678 lines, 0.0% -- also large,
`plan`/`doc`/`audit`/`export` verbs each need their own fixture). Still-open
deferred candidates (native/TS gap, out of scope for pure-Python coverage
work): `src/frob/check/_native.py`, `src/frob/check/_ts.py`,
`src/frob/dup/_legacy_cpp.py`. `src/frob/tickets/_store.py`'s two remaining
symbol-branch waivers (`migrate_to_ledger`, `atomic_write`) are close to
the floor (85.0%/88.9% vs. 90%) and a good small pickup for the next batch
alongside ticket_runner.py/sys_runner.py.

## Batch 7 Done report

Changed:
- No source-logic changes to `src/frob/app/ticket_runner.py` or
  `src/frob/app/sys_runner.py` (test-only coverage additions).
- `src/frob/tickets/_store.py`: removed the two remaining `frob:waive
  TEST005` directives on `migrate_to_ledger` and `atomic_write` (both now
  comfortably clear the 90% symbol-branch floor; no logic change).
- `tests/unit/test_app_runners_batch7.py` (new, 86 tests): direct-call
  `run(cfg)` coverage for `app/ticket_runner.py` (every subcommand's
  missing-arg/not-found/success/failure paths, including `_load_ticket_or_
  exit` load errors, clipboard-attach TTY flow, `land`/`renumber` success
  and failure via monkeypatched `frob.tickets.land`/`renumber_one`, start's
  auto-plan-then-transition-failure branch) and `app/sys_runner.py`
  (`plan`/`doc`/`export`/`audit`, each verb's no-models/malformed-design/
  bad-format/bad-view/apply-failure/waived-gap branches).
- `tests/unit/test_store_batch7.py` (new, 4 tests): `migrate_to_ledger`'s
  `atomic_write`-fails propagation and per-file unlink-`OSError`-is-warned
  branches; `atomic_write`'s bytes-content write mode and its nested
  `os.unlink`-also-fails-inside-`except OSError` branch.

Evidence: 90 new node ids recorded via `frob ticket evidence T-0160` (237
total). Representative:
`tests/unit/test_app_runners_batch7.py::TestTicketStart::test_start_auto_plans_queued_ticket`,
`tests/unit/test_app_runners_batch7.py::TestSysAudit::test_waived_gap_still_proves_clean`,
`tests/unit/test_app_runners_batch7.py::TestClipboardAttachOnNew::test_accepted_answer_attaches`,
`tests/unit/test_store_batch7.py::TestAtomicWrite::test_nested_unlink_failure_after_write_error_is_swallowed`.

Per-module before/after coverage (measured via targeted `uv run pytest
<file(s)> --cov=<module dir> --cov-branch --cov-report=term-missing
-p no:cacheprovider -q -n0`, per playbook 6b -- no `make coverage`/full
stamp run as a dispatched sub-agent):
- `src/frob/app/ticket_runner.py`: combined line+branch cover ~41% -> 89%
  (`--cov=src/frob/app` scoped run with
  `tests/unit/test_app_runners_batch7.py` + `tests/test_tickets_evidence_cli.py`)
- `src/frob/app/sys_runner.py`: combined line+branch cover ~0% -> 90%
  (same scoped run)
- `src/frob/tickets/_store.py`: `migrate_to_ledger`/`atomic_write` fully
  covered (no remaining misses in either function's line range) in a
  `--cov=src/frob/tickets` run over `tests/unit/test_store_batch7.py` +
  `tests/unit/test_claims_and_store_batch6.py` + `tests/unit/
  test_ticket_store.py` + `tests/test_tickets*.py` (module overall 78% ->
  91%); the two waivers are removed.

TEST005: both `ticket_runner.py`'s module-line waiver and `sys_runner.py`'s
module-line waiver remain on the two modules' `run` docstring line
comments in source (not removed this batch -- the coordinator's full-suite
`make coverage` + `frob check --stamp-coverage` re-stamp is the authority
for whether the 85%/90% floors hold against the WHOLE suite, not just this
batch's scoped runs; per-module numbers above are measured against this
batch's test files plus their modules' existing direct callers only, per
playbook 6b). `src/frob/tickets/_store.py`'s two symbol-branch waivers
(`migrate_to_ledger`, `atomic_write`) ARE removed -- their scoped
measurement showed 0 remaining misses in either function.

Gates: `uv run frob ticket sweep T-0160` (fresh pre-work sweep) then `uv run
frob check --ticket T-0160`: 1 error (`REL001`: public API changed since
0.27.0, needs a version bump + `frob release stamp`) -- pre-existing,
NOT caused by this batch (no public API surface touched; only test files
added and two waiver-comment lines removed from `_store.py`), 16 warnings,
37 waived. `uv run ruff check` and `uv run ruff format --check` both clean
(project-pinned `uv run ruff` AND PATH `ruff`) on every file this batch
touched. `pytest --collect-only` repo-wide is clean (no collection errors
introduced; all 90 batch-7 node ids resolve, confirmed via a fresh
`--collect-only` pass). All touched-set tests pass: `uv run pytest
tests/unit/test_app_runners_batch7.py tests/unit/test_store_batch7.py -q
-p no:cacheprovider` -- 90 passed, 0 failed. `git diff main
--diff-filter=D --stat` empty (no unintended deletions).

Filed: none (no out-of-scope work discovered this pass).

Not closing: T-0160 remains an explicitly multi-pass backlog. This batch
cleared its two named large-runner candidates
(`ticket_runner.py`/`sys_runner.py`) plus `tickets/_store.py`'s last two
symbol-branch waivers, all named in the batch-6 ledger note as the
priority pickups. Remaining deferred candidates (native/TS gap, out of
scope for pure-Python coverage work): `src/frob/check/_native.py`,
`src/frob/check/_ts.py`, `src/frob/dup/_legacy_cpp.py`. The coordinator
should re-run `make coverage` + `frob check --stamp-coverage` to get an
authoritative full-suite TEST005 count and confirm whether
`ticket_runner.py`/`sys_runner.py`'s module-line waivers can also be
removed against the whole suite (this batch's scoped per-module
percentages strongly suggest yes, but a scoped run is not the same
measurement the gate itself uses).

Ledger note (2026-07-20, batch 8): closed the FINAL 3 non-native TEST005 gaps
named in this batch's dispatch: `src/frob/testing/_collect.py::collect_python_tests`
(branch 87.0%->98%, measured via `uv run pytest tests/test_testing.py
--cov=frob.testing._collect --cov-branch`; only `133->137` (a submodule-package
artifact-glob branch already implicitly covered by the maturin-layout tests)
and `205->200` (a duplicate-cwd dedup loop continuation) plus two Rust
no-lib-target lines (`641-642`) remain uncovered -- all three are
sub-1%-of-module residue, well clear of the >=90% floor), `src/frob/strata/
_native_staleness.py::stale_natives` (branch 87.0%->99%, measured via `uv run
pytest tests/unit/strata/test_native_staleness.py --cov=frob.strata
._native_staleness --cov-branch`; only `84->79` remains, the "newest mtime
unchanged" loop-continuation branch, already implicitly exercised by every
multi-file `_newest_mtime` walk -- coverage.py just doesn't count the
non-updating iteration as a separate hit), and `src/frob/serve/__init__.py`
(line 50.0%->100%, direct tests for `__getattr__`'s lazy `McpUnavailable`/
`build_server`/`run_stdio` re-export and its unknown-name `AttributeError`
path -- no `frob:waive` was needed; `mcp` IS installed in this worktree's
`.venv`, so the "optional dependency absent" escape hatch in the ticket's
plan did not apply). All 3 modules carried NO existing `frob:waive TEST005`
directive to remove (their gaps were freshly discovered by this batch's
dispatch, not previously waived debt). New tests: 19 in
`tests/test_testing.py::TestCollectBranchGaps`, 7 in `tests/unit/strata/
test_native_staleness.py::TestNativeStalenessBranchGaps`, 2 in
`tests/test_serve.py::TestServeGetattr` -- 28 total, all direct/unit-level
error-and-degraded-path tests (spawn failures, malformed TOML, OSError on
stat/read, find_spec raising, unknown attribute access), not coverage
theater. Per prompt instruction, `src/frob/arch/_python.py
::collect_file_dispatch_refs` (T-0371, a DIFFERENT module) was explicitly
left untouched.

Per the prompt's framing, all 3 gaps named as "the FINAL 3 non-native TEST005
gaps" for this batch are now closed. Only native/TS modules remain in the
backlog per the batch-7 note above (`src/frob/check/_native.py`,
`src/frob/check/_ts.py`, `src/frob/dup/_legacy_cpp.py`) -- coordinator's call
on whether/how to proceed on those.

## Done report (batch 8)

Changed:
- `tests/test_testing.py::TestCollectBranchGaps` (19 new tests, test-only)
- `tests/unit/strata/test_native_staleness.py::TestNativeStalenessBranchGaps`
  (7 new tests, test-only)
- `tests/test_serve.py::TestServeGetattr` (2 new tests, test-only)

No source changes -- this batch is test-only, closing pure coverage gaps.

Evidence: 28 new node ids recorded via `frob ticket evidence T-0160` (265
total accumulated). Representative ids: `tests/test_testing.py
::TestCollectBranchGaps::test_run_collect_only_spawn_failure_is_err`,
`tests/unit/strata/test_native_staleness.py
::TestNativeStalenessBranchGaps::test_artifact_mtime_unstatable_artifact_is_none`,
`tests/test_serve.py::TestServeGetattr::test_getattr_resolves_lazy_server_names`.

Per-module before/after coverage (measured via targeted `uv run pytest
<test file> --cov=<module> --cov-branch --cov-report=term-missing
-p no:cacheprovider -n0 -q`, then confirmed against a full `make coverage`
+ `frob check --stamp-coverage` re-stamp):
- `src/frob/testing/_collect.py::collect_python_tests`: branch 87.0% -> 98%
- `src/frob/strata/_native_staleness.py::stale_natives`: branch 87.0% -> 99%
- `src/frob/serve/__init__.py`: line 50.0% -> 100%

Gates: `uv run frob ticket sweep T-0160` (fresh pre-work sweep) then `uv run
frob check --ticket T-0160`: 4 errors remaining, all pre-existing and out of
this batch's scope -- `COV001`/`TEST001` on `src/frob/arch/_python.py
::collect_file_dispatch_refs` (T-0371, explicitly a DIFFERENT module per the
dispatch prompt, not touched), and `REL001` x2 (public API version bump +
CHANGELOG entry needed since 0.28.0 -- pre-existing repo-wide release-
tracking state, no public API surface touched by this test-only batch); 15
warnings, 138 waived. `uv run ruff check` and `uv run ruff format --check`
clean (project-pinned `uv run ruff`) on all 3 touched test files. `pytest
--collect-only` repo-wide clean (all 28 new node ids resolve, confirmed via
a fresh `--collect-only` pass). All touched-set tests pass: `uv run pytest
tests/test_testing.py tests/unit/strata/test_native_staleness.py
tests/test_serve.py -p no:cacheprovider -n0 -q` -- 106 passed, 0 failed
(full files, not just the new classes). Full-suite `make coverage` +
`frob check --stamp-coverage` also ran clean (all tests pass, stamp written,
source_sha=0e3dfed3). `git diff main --diff-filter=D --stat` empty (no
unintended deletions).

Filed: none (no out-of-scope work discovered this pass; T-0371's
`collect_file_dispatch_refs` gap was noted per the dispatch prompt but
deliberately not touched -- it is a separate, already-known ticket).

Not closing: T-0160 remains an explicitly multi-pass backlog per the
coordinator's earlier direction -- only native/TS modules are believed to
remain (`src/frob/check/_native.py`, `src/frob/check/_ts.py`,
`src/frob/dup/_legacy_cpp.py`), pending coordinator confirmation via a fresh
full-suite `frob check --only test` scan.
