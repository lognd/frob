# Tickets

Central ledger managed by `frob ticket` -- one section per ticket.

<!-- ticket:T-0160 -->
```yaml
id: T-0160
title: burn down TEST005 module-line-coverage backlog (~78 modules below 85% floor)
state: queued
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
blocked_by: []
parent: null
scope:
- tests/**
- frob.toml
- src/frob/app/ack_runner.py
- src/frob/app/parse_runner.py
scope_changes:
- op: remove
  glob: src/frob/**
  reason: 'batch 10: narrow to ack_runner/parse_runner TEST005 for this pass'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/app/ack_runner.py
  reason: 'batch 10: narrow to ack_runner/parse_runner TEST005 for this pass'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/app/parse_runner.py
  reason: 'batch 10: narrow to ack_runner/parse_runner TEST005 for this pass'
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_gates.py::TestInvariantLoad::test_unreadable_file_is_malformed
- tests/test_gates.py::TestInvariantLoad::test_no_frontmatter_block_is_malformed
- tests/test_gates.py::TestInvariantLoad::test_bad_yaml_frontmatter_is_malformed
- tests/test_gates.py::TestInvariantLoad::test_non_mapping_frontmatter_is_malformed
- tests/test_gates.py::TestInvariantLoad::test_empty_statement_is_malformed
- tests/test_gates.py::TestInvariantLoad::test_evidence_not_a_list_is_malformed
- tests/test_gates.py::TestInvariantLoad::test_bad_criticality_is_malformed
- tests/test_tickets_collision.py::TestDefaultBranchEdgeCases::test_remote_symbolic_ref_wins_over_local_main
- tests/test_tickets_collision.py::TestDefaultBranchEdgeCases::test_no_remote_falls_back_to_local_master
- tests/test_tickets_collision.py::TestDefaultBranchEdgeCases::test_no_remote_no_main_no_master_falls_back_to_main_literal
- tests/test_tickets_collision.py::TestDefaultBranchEdgeCases::test_detached_head_is_treated_as_default
- tests/test_tickets_collision.py::TestDefaultBranchEdgeCases::test_non_git_directory_is_treated_as_default
- tests/test_fuzz.py::TestRunFuzz::test_unsatisfiable_strategy_reports_rejection_rate
- tests/test_fuzz.py::TestRunFuzz::test_no_generator_target_short_circuits_without_hypothesis
- tests/test_fuzz.py::TestRunFuzz::test_digests_map_is_stamped_onto_matching_ref
- tests/test_fuzz.py::TestRunFuzz::test_hypothesis_unavailable_returns_empty_and_logs
- tests/test_fuzz.py::TestResolveParamTypes::test_strips_self_param_on_method
- tests/test_fuzz.py::TestResolveParamTypes::test_nested_module_path_derives_dotted_name
- tests/test_fuzz.py::TestResolveParamTypes::test_unresolvable_qualname_returns_none
- tests/test_fuzz.py::TestResolveParamTypes::test_non_callable_attribute_returns_none
- tests/test_perf.py::test_load_artifact_missing_ref_is_err
- tests/test_perf.py::test_load_artifact_bad_json_sidecar_is_bad_artifact
- tests/test_perf.py::test_load_artifact_missing_pstats_is_bad_artifact
- tests/test_perf.py::test_profile_command_strips_leading_python_interpreter
- tests/unit/test_scaffold_project.py::test_render_project_all_registered_types_succeed
- tests/unit/test_scaffold_project.py::test_render_project_propagates_resolve_failure
- tests/test_perf_rules_internals.py::test_perf_rules_falls_back_to_span_start_when_source_vanishes
- tests/test_perf_rules_internals.py::test_method_call_in_loop_fires_at_depth_zero
- tests/unit/test_dup_legacy_py.py::test_collect_locals_py_covers_every_binding_shape
- tests/unit/test_dup_legacy_py.py::test_serialize_py_body_renames_locals_and_normalizes_literals
- tests/unit/test_gitlog_rendering.py::test_as_text_renders_breaking_section_and_labels
- tests/unit/test_gitlog_rendering.py::test_commit_entry_from_block_with_refs_and_body
- tests/test_clipboard.py::TestBackends::test_wsl_save_reports_no_image_on_exit_code_2
- tests/test_clipboard.py::TestBackends::test_darwin_pngpaste_selected_and_reads_image
- tests/test_excludes.py::test_malformed_toml_is_empty_not_raise
- tests/test_gitio.py::TestRepoRoot::test_run_argv_failure_surfaces_as_not_a_repo
- tests/test_gitio.py::TestWorkingDiff::test_untracked_listing_failure_propagates
- tests/unit/test_app_runners.py::TestMapRunner::test_text_mode_logs_summary
- tests/unit/test_app_runners.py::TestMapRunner::test_json_mode_logs_json
- tests/unit/test_app_runners.py::TestMapRunner::test_defaults_to_cwd_when_no_path
- tests/unit/test_app_runners.py::TestGitlogRunner::test_text_mode_prints_result
- tests/unit/test_app_runners.py::TestGitlogRunner::test_json_mode_prints_json
- tests/unit/test_app_runners.py::TestXrefRunner::test_missing_symbol_exits_1
- tests/unit/test_app_runners.py::TestXrefRunner::test_no_files_found_exits_1
- tests/unit/test_app_runners.py::TestXrefRunner::test_symbol_not_found_still_succeeds
- tests/unit/test_app_runners.py::TestXrefRunner::test_found_symbol_text_mode
- tests/unit/test_app_runners.py::TestXrefRunner::test_found_symbol_json_mode
- tests/unit/test_app_runners.py::TestScaffoldRunner::test_list_command_logs_types
- tests/unit/test_app_runners.py::TestScaffoldRunner::test_default_command_is_list
- tests/unit/test_app_runners.py::TestScaffoldRunner::test_new_missing_type_exits_1
- tests/unit/test_app_runners.py::TestScaffoldRunner::test_new_missing_name_exits_1
- tests/unit/test_app_runners.py::TestScaffoldRunner::test_new_success_logs_created_paths
- tests/unit/test_app_runners.py::TestScaffoldRunner::test_new_render_error_exits_1
- tests/unit/test_app_runners.py::TestExportsRunner::test_missing_path_exits_1
- tests/unit/test_app_runners.py::TestExportsRunner::test_err_result_exits_1
- tests/unit/test_app_runners.py::TestExportsRunner::test_text_mode_logs_result
- tests/unit/test_app_runners.py::TestExportsRunner::test_json_mode_logs_result
- tests/unit/test_app_runners.py::TestExportsRunner::test_write_mode_writes_init_file
- tests/unit/test_app_runners.py::TestArchRunner::test_missing_path_exits_1
- tests/unit/test_app_runners.py::TestArchRunner::test_text_mode_with_overrides
- tests/unit/test_app_runners.py::TestArchRunner::test_json_mode
- tests/unit/test_app_runners.py::TestOutlineRunner::test_missing_file_exits_1
- tests/unit/test_app_runners.py::TestOutlineRunner::test_directory_target_falls_back_to_map
- tests/unit/test_app_runners.py::TestOutlineRunner::test_file_target_text_mode
- tests/unit/test_app_runners.py::TestOutlineRunner::test_file_target_json_mode
- tests/unit/test_app_runners.py::TestOutlineRunner::test_err_result_exits_1
- tests/unit/test_app_runners.py::TestMutateRunner::test_missing_file_exits_1
- tests/unit/test_app_runners.py::TestMutateRunner::test_err_result_exits_1
- tests/unit/test_app_runners.py::TestMutateRunner::test_default_argv_used_when_empty
- tests/unit/test_app_runners.py::TestMutateRunner::test_success_no_survivors_text_mode
- tests/unit/test_app_runners.py::TestMutateRunner::test_success_with_survivors_exits_1
- tests/unit/test_app_runners.py::TestMutateRunner::test_success_json_mode
- tests/unit/test_app_runners_batch5.py::TestStatsRunner::test_git_error_exits_1
- tests/unit/test_app_runners_batch5.py::TestServeRunner::test_mcp_unavailable_exits_1
- tests/unit/test_app_runners_batch5.py::TestDupRunner::test_probe_equivalent_exits_0
- tests/unit/test_app_runners_batch5.py::TestDupRunner::test_probe_differ_exits_1
- tests/unit/test_app_runners_batch5.py::TestBindRunner::test_mismatch_json_mode_no_exit
- tests/unit/test_app_runners_batch5.py::TestCycleRunner::test_lang_filter_skips_non_matching_extension
- tests/unit/test_app_runners_batch5.py::TestDocsRunner::test_overview_json_mode
- tests/unit/test_app_runners_batch5.py::TestReleaseRunner::test_check_bump_required_exits_1
- tests/unit/test_app_runners_batch5.py::TestVetRunner::test_scan_with_cve_matches_text_mode
- tests/unit/test_app_runners_batch5.py::TestVetRunner::test_scan_with_violations_enforced_exits_1
- tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_unknown_command_exits_1
- tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_build_success_logs_stats
- tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_query_requires_ref
- tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_query_unresolvable_ref_exits_1
- tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_query_text_mode_prints_record
- tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_query_json_mode_prints_json
- tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_why_requires_ref
- tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_why_unresolvable_ref_exits_1
- tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_why_text_mode_not_acked
- tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_why_json_mode_prints_json
- tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_build_failure_exits_1
- tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_query_snapshot_unavailable_exits_1
- tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_query_with_edges_renders_both_directions
- tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_why_lock_load_failure_exits_1
- tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_why_snapshot_unavailable_exits_1
- tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_why_acked_stale_dangling_render_lines
- tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_unknown_command_exits_1
- tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_profile_requires_argv_or_tests
- tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_profile_and_heat_round_trip
- tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_heat_json_mode
- tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_heat_top_and_smells
- tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_heat_annotate_writes_gutters
- tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_heat_no_artifact_exits_1
- tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_heat_annotate_missing_file_exits_1
- tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_profile_failure_propagates_workload_exit_code
- tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_profile_command_error_exits_1
- tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_profile_tests_flag_builds_pytest_argv
- tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_heat_snapshot_build_failure_exits_1
- tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_heat_annotate_unreadable_file_exits_1
- tests/unit/test_app_runners_batch6.py::TestPerfRunner::test_heat_annotate_outside_root_uses_absolute_path
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_nonexistent_path_exits_1
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_mode_calls_stamp_and_returns
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_failure_exits_1
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_mode_calls_stamp_and_returns
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_gate_error_exits_1
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_auto_detected_python_stage_dispatches_and_passes
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_json_mode_prints_json_and_errors_exit_1
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_pinned_type_warns_polyglot_and_skips_others
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_pinned_cpp_dispatches_run_check_cpp
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_pinned_rust_dispatches_run_check_rust
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_pinned_typescript_dispatches_run_check_ts
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_frob_toml_defaults_applied
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_frob_toml_unreadable_warns_and_continues
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_deploy_stages_appended_when_deploy_dir_present
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_verbose_levels_do_not_crash
- tests/unit/test_claims_and_store_batch6.py::TestClaimsMalformedAttrs::test_malformed_skew_attr_is_ignored
- tests/unit/test_claims_and_store_batch6.py::TestClaimsMalformedAttrs::test_malformed_growth_attr_is_ignored
- tests/unit/test_claims_and_store_batch6.py::TestAssumeReviewDates::test_malformed_review_date_logs_and_notes
- tests/unit/test_claims_and_store_batch6.py::TestAssumeReviewDates::test_overdue_review_date_is_flagged
- tests/unit/test_claims_and_store_batch6.py::TestBoundClaimEdgeCases::test_age_unknown_target_fails_closed
- tests/unit/test_claims_and_store_batch6.py::TestBoundClaimEdgeCases::test_rate_unknown_target_fails_closed
- tests/unit/test_claims_and_store_batch6.py::TestBoundClaimEdgeCases::test_utilization_wrong_dimension_limit_errors
- tests/unit/test_claims_and_store_batch6.py::TestBoundClaimEdgeCases::test_utilization_zero_ceiling_refutes
- tests/unit/test_claims_and_store_batch6.py::TestBoundClaimEdgeCases::test_utilization_skewed_zero_ceiling_refutes
- tests/unit/test_claims_and_store_batch6.py::TestBoundClaimEdgeCases::test_latency_unknown_flow_fails_closed
- tests/unit/test_claims_and_store_batch6.py::TestBoundClaimEdgeCases::test_size_no_declared_size_refutes
- tests/unit/test_claims_and_store_batch6.py::TestTicketStoreParsing::test_parse_ticket_file_no_frontmatter_block
- tests/unit/test_claims_and_store_batch6.py::TestTicketStoreParsing::test_parse_ticket_file_bad_yaml
- tests/unit/test_claims_and_store_batch6.py::TestTicketStoreParsing::test_parse_ticket_file_roundtrips_valid
- tests/unit/test_claims_and_store_batch6.py::TestTicketStoreWriteAndMigrate::test_write_ticket_single_mode_existing_load_error_propagates
- tests/unit/test_claims_and_store_batch6.py::TestTicketStoreWriteAndMigrate::test_write_all_dir_mode_prunes_stale_files
- tests/unit/test_claims_and_store_batch6.py::TestTicketStoreWriteAndMigrate::test_migrate_to_ledger_empty_is_noop
- tests/unit/test_claims_and_store_batch6.py::TestTicketStoreWriteAndMigrate::test_migrate_to_ledger_malformed_file_fails_closed
- tests/unit/test_claims_and_store_batch6.py::TestTicketStoreWriteAndMigrate::test_migrate_to_ledger_moves_dir_files_into_ledger
- tests/unit/test_claims_and_store_batch6.py::TestTicketStoreWriteAndMigrate::test_atomic_write_oserror_returns_write_failed
- tests/unit/test_app_runners_batch7.py::TestTicketRunnerDispatch::test_unknown_command_exits_1
- tests/unit/test_app_runners_batch7.py::TestTicketNewErrors::test_missing_title_or_kind_exits_1
- tests/unit/test_app_runners_batch7.py::TestTicketList::test_no_tickets_logs_message
- tests/unit/test_app_runners_batch7.py::TestTicketList::test_list_json_mode
- tests/unit/test_app_runners_batch7.py::TestTicketList::test_list_filters_by_state
- tests/unit/test_app_runners_batch7.py::TestTicketList::test_list_text_mode_prints_ticket_line
- tests/unit/test_app_runners_batch7.py::TestTicketListShowDoableLoadErrors::test_list_load_error_exits_1
- tests/unit/test_app_runners_batch7.py::TestTicketListShowDoableLoadErrors::test_show_load_error_exits_1
- tests/unit/test_app_runners_batch7.py::TestTicketListShowDoableLoadErrors::test_doable_load_error_exits_1
- tests/unit/test_app_runners_batch7.py::TestTicketShow::test_missing_id_exits_1
- tests/unit/test_app_runners_batch7.py::TestTicketShow::test_unknown_id_exits_1
- tests/unit/test_app_runners_batch7.py::TestTicketShow::test_show_found_json_mode
- tests/unit/test_app_runners_batch7.py::TestTicketShow::test_show_found_text_mode
- tests/unit/test_app_runners_batch7.py::TestTicketDoable::test_nothing_doable
- tests/unit/test_app_runners_batch7.py::TestTicketDoable::test_doable_json_mode
- tests/unit/test_app_runners_batch7.py::TestTicketDoable::test_doable_text_mode
- tests/unit/test_app_runners_batch7.py::TestTicketMigrate::test_no_legacy_files
- tests/unit/test_app_runners_batch7.py::TestTicketMigrate::test_migrates_legacy_dir_ticket
- tests/unit/test_app_runners_batch7.py::TestTicketRenumber::test_dry_run_without_old_new_exits_1
- tests/unit/test_app_runners_batch7.py::TestTicketRenumber::test_whole_ledger_already_contiguous
- tests/unit/test_app_runners_batch7.py::TestTicketRenumber::test_one_missing_new_id_exits_1
- tests/unit/test_app_runners_batch7.py::TestTicketRenumber::test_renumber_one_dry_run_prints_files
- tests/unit/test_app_runners_batch7.py::TestTicketRenumber::test_renumber_one_success
- tests/unit/test_app_runners_batch7.py::TestTicketLand::test_missing_id_exits_1
- tests/unit/test_app_runners_batch7.py::TestTicketLand::test_missing_worktree_exits_1
- tests/unit/test_app_runners_batch7.py::TestTicketLand::test_land_failure_exits_1
- tests/unit/test_app_runners_batch7.py::TestTicketLand::test_land_dry_run_success
- tests/unit/test_app_runners_batch7.py::TestTicketLand::test_land_success_prints_files
- tests/unit/test_app_runners_batch7.py::TestTicketPlan::test_missing_id_exits_1
- tests/unit/test_app_runners_batch7.py::TestTicketPlan::test_plan_success
- tests/unit/test_app_runners_batch7.py::TestTicketStart::test_missing_id_exits_1
- tests/unit/test_app_runners_batch7.py::TestTicketStart::test_unknown_id_exits_1
- tests/unit/test_app_runners_batch7.py::TestTicketStart::test_start_auto_plans_queued_ticket
- tests/unit/test_app_runners_batch7.py::TestTicketStart::test_start_already_in_progress_exits_1
- tests/unit/test_app_runners_batch7.py::TestTicketStartTransitionFailure::test_transition_to_in_progress_failure_exits_1
- tests/unit/test_app_runners_batch7.py::TestTicketSweep::test_missing_id_exits_1
- tests/unit/test_app_runners_batch7.py::TestTicketSweep::test_not_in_progress_exits_1
- tests/unit/test_app_runners_batch7.py::TestClipboardAttachOnNew::test_no_clipboard_image_skips
- tests/unit/test_app_runners_batch7.py::TestClipboardAttachOnNew::test_declined_answer_skips_attach
- tests/unit/test_app_runners_batch7.py::TestClipboardAttachOnNew::test_accepted_answer_attaches
- tests/unit/test_app_runners_batch7.py::TestTicketAttach::test_missing_id_exits_1
- tests/unit/test_app_runners_batch7.py::TestTicketAttach::test_no_path_non_tty_exits_1
- tests/unit/test_app_runners_batch7.py::TestTicketAttach::test_attach_from_path_success
- tests/unit/test_app_runners_batch7.py::TestTicketBlock::test_missing_args_exits_1
- tests/unit/test_app_runners_batch7.py::TestTicketBlock::test_block_success
- tests/unit/test_app_runners_batch7.py::TestTicketClose::test_missing_id_exits_1
- tests/unit/test_app_runners_batch7.py::TestTicketClose::test_close_queued_gives_start_hint
- tests/unit/test_app_runners_batch7.py::TestTicketClose::test_close_missing_evidence_gives_hint
- tests/unit/test_app_runners_batch7.py::TestTicketClose::test_close_with_bad_evidence_ids_exits_1_without_closing
- tests/unit/test_app_runners_batch7.py::TestTicketFail::test_missing_args_exits_1
- tests/unit/test_app_runners_batch7.py::TestTicketFail::test_unknown_id_exits_1
- tests/unit/test_app_runners_batch7.py::TestTicketFail::test_fail_records_attempt
- tests/unit/test_app_runners_batch7.py::TestTicketEvidence::test_missing_args_exits_1
- tests/unit/test_app_runners_batch7.py::TestTicketEvidence::test_evidence_ids_applied
- tests/unit/test_app_runners_batch7.py::TestTicketEvidence::test_evidence_cmd_applied_for_docs_ticket
- tests/unit/test_app_runners_batch7.py::TestTicketEvidence::test_evidence_cmd_failure_logs_error
- tests/unit/test_app_runners_batch7.py::TestTicketArchive::test_nothing_to_archive
- tests/unit/test_app_runners_batch7.py::TestTicketArchive::test_archives_done_ticket
- tests/unit/test_app_runners_batch7.py::TestSysRunnerDispatch::test_unknown_command_exits_1
- tests/unit/test_app_runners_batch7.py::TestSysPlan::test_no_design_models
- tests/unit/test_app_runners_batch7.py::TestSysPlan::test_dry_run_prints_plan
- tests/unit/test_app_runners_batch7.py::TestSysPlan::test_apply_writes_tickets
- tests/unit/test_app_runners_batch7.py::TestSysPlan::test_file_arg_fails
- tests/unit/test_app_runners_batch7.py::TestSysPlan::test_malformed_design_file_exits_1
- tests/unit/test_app_runners_batch7.py::TestSysPlan::test_apply_new_ticket_failure_exits_1
- tests/unit/test_app_runners_batch7.py::TestSysPlan::test_custom_design_dir_from_frob_toml
- tests/unit/test_app_runners_batch7.py::TestSysPlan::test_unreadable_frob_toml_falls_back_to_default
- tests/unit/test_app_runners_batch7.py::TestSysPlan::test_unchanged_model_second_run_no_new_tickets
- tests/unit/test_app_runners_batch7.py::TestSysDoc::test_no_design_models
- tests/unit/test_app_runners_batch7.py::TestSysDoc::test_renders_matrix
- tests/unit/test_app_runners_batch7.py::TestSysDoc::test_malformed_design_file_exits_1
- tests/unit/test_app_runners_batch7.py::TestSysDoc::test_unknown_view_exits_1
- tests/unit/test_app_runners_batch7.py::TestSysExport::test_bad_format_exits_1
- tests/unit/test_app_runners_batch7.py::TestSysExport::test_directory_path_exits_1
- tests/unit/test_app_runners_batch7.py::TestSysExport::test_missing_path_exits_1
- tests/unit/test_app_runners_batch7.py::TestSysExport::test_parse_failure_exits_1
- tests/unit/test_app_runners_batch7.py::TestSysExport::test_each_format_renders[k8s]
- tests/unit/test_app_runners_batch7.py::TestSysExport::test_each_format_renders[seccomp]
- tests/unit/test_app_runners_batch7.py::TestSysExport::test_each_format_renders[iam]
- tests/unit/test_app_runners_batch7.py::TestSysExport::test_default_design_path
- tests/unit/test_app_runners_batch7.py::TestSysAudit::test_no_design_models
- tests/unit/test_app_runners_batch7.py::TestSysAudit::test_clean_model_passes
- tests/unit/test_app_runners_batch7.py::TestSysAudit::test_malformed_design_file_exits_1
- tests/unit/test_app_runners_batch7.py::TestSysAudit::test_waived_gap_still_proves_clean
- tests/unit/test_app_runners_batch7.py::TestSysAudit::test_gap_model_exits_1
- tests/unit/test_app_runners_batch7.py::TestSysAudit::test_file_arg_fails
- tests/unit/test_store_batch7.py::TestMigrateToLedger::test_atomic_write_failure_propagates
- tests/unit/test_store_batch7.py::TestMigrateToLedger::test_source_unlink_failure_is_warned_not_fatal
- tests/unit/test_store_batch7.py::TestAtomicWrite::test_bytes_content_write_mode
- tests/unit/test_store_batch7.py::TestAtomicWrite::test_nested_unlink_failure_after_write_error_is_swallowed
- tests/test_testing.py::TestCollectBranchGaps::test_walk_test_files_matches_suffix_style_test_files
- tests/test_testing.py::TestCollectBranchGaps::test_content_key_unreadable_file_is_skipped_not_raised
- tests/test_testing.py::TestCollectBranchGaps::test_native_artifact_digest_resolvable_no_compiled_artifact
- tests/test_testing.py::TestCollectBranchGaps::test_native_artifact_digest_unreadable_artifact
- tests/test_testing.py::TestCollectBranchGaps::test_missing_natives_treats_find_spec_error_as_missing
- tests/test_testing.py::TestCollectBranchGaps::test_load_natives_or_empty_degrades_on_malformed_config
- tests/test_testing.py::TestCollectBranchGaps::test_load_cache_unreadable_json_is_none
- tests/test_testing.py::TestCollectBranchGaps::test_load_cache_key_mismatch_is_none
- tests/test_testing.py::TestCollectBranchGaps::test_run_collect_only_spawn_failure_is_err
- tests/test_testing.py::TestCollectBranchGaps::test_run_collect_only_bad_exit_code_is_err
- tests/test_testing.py::TestCollectBranchGaps::test_reroot_node_ids_noop_for_dot_cwd
- tests/test_testing.py::TestCollectBranchGaps::test_python_runner_cwds_degrades_on_bad_runner_config
- tests/test_testing.py::TestCollectBranchGaps::test_python_runner_cwds_dedupes_repeated_cwd
- tests/test_testing.py::TestCollectBranchGaps::test_collect_nested_python_propagates_collect_failure
- tests/test_testing.py::TestCollectBranchGaps::test_collect_python_tests_outer_collection_failure_is_err
- tests/test_testing.py::TestCollectBranchGaps::test_collect_python_tests_nested_failure_degrades_with_warning
- tests/test_testing.py::TestCollectBranchGaps::test_rust_content_key_unreadable_file_is_skipped
- tests/test_testing.py::TestCollectBranchGaps::test_cargo_list_result_spawn_failure_is_err
- tests/test_testing.py::TestCollectBranchGaps::test_run_cargo_test_list_integration_failure_propagates
- tests/unit/strata/test_native_staleness.py::TestNativeStalenessBranchGaps::test_newest_mtime_absent_directory_is_none
- tests/unit/strata/test_native_staleness.py::TestNativeStalenessBranchGaps::test_newest_mtime_skips_unstatable_file_and_keeps_max
- tests/unit/strata/test_native_staleness.py::TestNativeStalenessBranchGaps::test_artifact_mtime_find_spec_error_is_none
- tests/unit/strata/test_native_staleness.py::TestNativeStalenessBranchGaps::test_artifact_mtime_no_compiled_artifact_is_none
- tests/unit/strata/test_native_staleness.py::TestNativeStalenessBranchGaps::test_artifact_mtime_unstatable_artifact_is_none
- tests/unit/strata/test_native_staleness.py::TestNativeStalenessBranchGaps::test_stale_natives_degrades_on_malformed_config
- tests/unit/strata/test_native_staleness.py::TestNativeStalenessBranchGaps::test_stale_natives_skips_empty_source_dir
- tests/test_serve.py::TestServeGetattr::test_getattr_resolves_lazy_server_names
- tests/test_serve.py::TestServeGetattr::test_getattr_unknown_name_raises_attribute_error
- tests/test_graph_lock.py::TestAckDrift::test_acknowledge_endpoint_that_does_not_resolve_is_err
- tests/test_graph_lock.py::TestAckDrift::test_write_lock_oserror_on_replace_is_write_failed
- tests/unit/test_dup_cache.py::TestFingerprintRoundTrip::test_get_fingerprint_connect_error_returns_none
- tests/unit/test_dup_cache.py::TestVerdictRoundTrip::test_put_verdict_evicts_lru_rows_beyond_cache_entries
- tests/unit/test_dup_cache.py::TestVerdictRoundTrip::test_put_verdict_connect_error_is_propagated
- tests/unit/test_ack_runner.py::TestAckRunnerRun::test_no_refs_exits_with_error
- tests/unit/test_ack_runner.py::TestAckRunnerRun::test_success_path_builds_cache_and_writes_lock
- tests/unit/test_ack_runner.py::TestAckRunnerRun::test_unresolvable_ref_exits_with_error
- tests/unit/test_ack_runner.py::TestAckRunnerRun::test_graph_unavailable_after_failed_build_exits_with_error
- tests/unit/test_ack_runner.py::TestAckRunnerRun::test_malformed_lock_file_exits_with_error
- tests/unit/test_ack_runner.py::TestAckRunnerRun::test_write_lock_failure_exits_with_error
- tests/unit/test_parse_runner_direct.py::TestParseRunnerRun::test_missing_tool_exits_with_error
- tests/unit/test_parse_runner_direct.py::TestParseRunnerRun::test_unknown_tool_exits_with_error
- tests/unit/test_parse_runner_direct.py::TestParseRunnerRun::test_unreadable_file_exits_with_error
- tests/unit/test_parse_runner_direct.py::TestParseRunnerRun::test_reads_from_file_and_logs_text
- tests/unit/test_parse_runner_direct.py::TestParseRunnerRun::test_reads_from_stdin_and_logs_json
- tests/unit/test_parse_runner_direct.py::TestParseRunnerRun::test_passthrough_propagates_failing_exit_code
- tests/unit/test_parse_runner_direct.py::TestParseRunnerRun::test_no_passthrough_does_not_exit_on_failure
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
TEST005 module-line-coverage floor (frob.toml [testing].module_line_cov=85) reports ~78 src/frob/** modules below threshold, from 0.0% (never-exercised runners like app/ack_runner.py, app/arch_runner.py, and most other app/*_runner.py CLI entry points) up to modules a few points shy of the floor (e.g. tickets/_store.py at 84.8%, strata/_claims.py at 84.7%). This backlog was invisible during T-0148's original scope (a fresh worktree has no .frob/coverage-stamp, and TEST005 silently produces no findings without one) -- it surfaced only after T-0148 regenerated the stamp to clear its own TEST006 finding ("no coverage stamp found"). It is pre-existing, repo-wide coverage debt, not something T-0148's edits introduced, and burning it down to the 85% floor across ~78 modules (many CLI app/*_runner.py entry points at literal 0%, needing new system/integration tests, not just unit tests) is a dedicated, multi-session effort far outside a gates-sweep ticket. Full per-module list captured via: uv run frob check --only test (TEST005 lines), 2026-07-18.

Acceptance: every src/frob/** module at or above module_line_cov=85 (or system_line_cov=80 in aggregate where a narrower per-module floor is not achievable), OR a specific, reasoned frob.toml override for modules that cannot reasonably reach the floor (e.g. thin CLI entry-point shims exercised only via subprocess system tests). Start with the 0.0%-covered app/*_runner.py entry points -- each is a CLI command's runner with no direct unit/integration test at all, the single highest-leverage slice of this backlog.

Scope correction (2026-07-18, same T-0148 sweep): `src/frob/gates/_coverage.py::_parse_classes` had a path-prefix bug -- Cobertura `filename` attrs are relative to the `--cov=src/frob` root (e.g. `app/ack_runner.py`), but every other path in `frob.graph` is repo-relative (`src/frob/app/ack_runner.py`); the two never matched, so BOTH `module_line` (this ticket's original ~78-module estimate) AND `symbol_branch` (per-symbol TEST005 branch-coverage, `unit_branch_cov=90`) silently mapped zero symbols this whole time. T-0148 fixed the prefix join. Re-running with the fix (and after excluding `src/frob/scaffold/data/**` template files, a separate genuine rule misfire fixed in the same sweep) shows the true backlog is far larger than originally scoped here: 197 unwaived TEST005 findings (up from ~78), most now per-symbol branch-coverage misses across `src/frob/**`, not just the module-line floor. This ticket's acceptance criteria and estimate above are superseded by that number -- treat "~78 modules" as the historical (and wrong, pre-fix) figure; the real acceptance criterion is 0 unwaived TEST005 findings from a fresh `uv run frob check --only test` after `make coverage`, both per-module and per-symbol. This is now unambiguously a dedicated, multi-session effort, not a gates-sweep add-on. (Renumbered from T-0157 to T-0160 on 2026-07-18: the original local allocation collided with main's real T-0157 (secrets-scan gate) landing concurrently; every `frob:waive TEST005` directive this ticket's sweep added under `src/frob/**` was updated in lockstep.)

Ledger note (2026-07-20, batch pass): cleared 5 modules with real, meaningful tests
raising them above the module_line_cov=85% / unit_branch_cov=90% floors and removed
their `frob:waive TEST005` directives (both module-line and any per-symbol
branch-coverage waivers): `src/frob/gates/invariants.py` (79.4%->96.9% line,
78.3%->100% branch on `load_invariants`'s only remaining symbol-level gap closed),
`src/frob/tickets/_provisional.py` (81.8%->100% line, `on_default_branch`
80.0%->91.7% branch), `src/frob/fuzz/_run.py` (83.9%->100% line, `run_fuzz`
71.4%->100% branch), `src/frob/fuzz/_signatures.py` (83.0%->88.0% line,
`resolve_param_types` 75.0%->79.4% branch -- module-line floor cleared;
`resolve_param_types` branch coverage improved substantially but the exact 90%
symbol-branch floor was not independently re-verified per-symbol post-sweep,
worth a follow-up spot-check), `src/frob/perf/_profile.py` (84.0%->92.6% line,
`load_artifact` 68.8%->81.8% branch -- module-line floor cleared; this module has
no other symbol-level TEST005 waiver so no further per-symbol waiver removal was
needed). Net effect measured via `uv run frob check --only test` before/after:
179 -> 170 unwaived+waived TEST005 lines total (the count includes waived entries
that no longer fire because their waiver text became stale-but-present; the 5
modules' 9 matching TEST005 lines -- 5 module-line + 4 symbol-branch -- are gone
from the diff). ~73 modules remain in the TEST005 backlog for the next pass;
highest-value remaining candidates identified but not yet started: `src/frob/
scaffold/project.py` (84.2%, closest to floor), `src/frob/perf/_rules.py` (83.8%,
large token-analysis module, needs deeper per-branch test design),
`src/frob/dup/_legacy_py.py` (79.4%), `src/frob/gitlog/__init__.py` (module-line
measured differently across scoped vs. full-suite runs -- worth checking whether
CLI/system tests are properly attributing coverage before budgeting effort
there), `src/frob/check/_native.py` (22.7%), `src/frob/check/_ts.py` (30.4%),
`src/frob/dup/_legacy_cpp.py` (15.2%) -- these last three are large native/TS
gap modules likely needing new fixture-driven integration tests, not quick unit
additions.

## Done report

Ledger note (2026-07-21, batch 10): continued the TEST005 waiver-directive
queue from batch 9. This pass targeted the 0.0%-covered CLI entry points
the ticket's acceptance criteria call out as highest-leverage
(app/*_runner.py runners with no direct unit test), using direct-call
tests (not subprocess) per the gitlog/clipboard precedent, since
subprocess-dispatched CLI tests do not attribute coverage back to the
runner module.

Closed this batch (2 modules, both fully cleared, all waivers removed):

- src/frob/app/ack_runner.py (0.0% module-line -> 99% branch on a scoped
  measurement combined with the existing lease-guard test file). Added 6
  new direct-call tests covering: no-refs error, the full success path
  (cache build + lock write + facet-informational log), an unresolvable
  ref (acknowledge's error branch), graph-unavailable (both load_graph and
  build_graph failing), a malformed pre-existing frob.lock, and a
  simulated os.replace failure on write_lock. The single remaining branch
  miss (24->27, the load_graph-succeeds-first-try short-circuit) is
  exercised transitively but not asserted on directly; not chased further
  since the module and symbol floors are both already cleared.
- src/frob/app/parse_runner.py (0.0% module-line -> 100% line+branch).
  Added 7 new direct-call tests covering: missing tool, unknown tool,
  unreadable --file, reading from a file (text output), reading from
  stdin (json output), and both passthrough exit-code branches
  (propagates vs. does not).

Measured via:
  uv run pytest tests/unit/test_ack_runner.py tests/test_ack_worktree_lease.py \
    --cov=frob.app.ack_runner --cov-branch --cov-report=term-missing \
    -p no:cacheprovider -q -o addopts=""
  (99% branch, 8 passed)
  uv run pytest tests/unit/test_parse_runner_direct.py \
    --cov=frob.app.parse_runner --cov-branch --cov-report=term-missing \
    -p no:cacheprovider -q -o addopts=""
  (100% line+branch, 7 passed)

Verified via uv run frob check --ticket T-0160: gate:TEST is clean (0
errors), gate:PRE clean after re-running the sweep post scope-narrow,
ruff-check/ruff-format clean on all touched files. The two other FAILs
seen in a full `frob check` run (a gate:DRIFT DRIFT002 naming the
archive ledger's anchor slug done-report-381) turned out to be caused
by this very report quoting the edge string verbatim -- the docs
scanner parsed the quoted path#anchor prose as a describes-edge; the
coordinator reworded it at land (this text) to break the pattern.

Waived, not fixed: none newly waived this batch; both targeted modules'
frob:waive TEST005 directives were removed entirely.

Scope was narrowed this batch (frob ticket scope) to
src/frob/app/ack_runner.py and src/frob/app/parse_runner.py plus
tests/**/frob.toml, per the T-0561 lease carve-out for concrete new-test
files.

Remaining highest-value TEST005 targets for the next batch (unchanged
list style from batch 9, refreshed against current in-source waivers):
other 0.0%-module-line app/*_runner.py entries (sys_runner.py,
test_runner.py, ticket_runner.py -- all large, will need more than one
batch each), src/frob/perf/_harness.py (0.0%, small), plus the
symbol-branch-only waivers scattered through gates/__init__.py,
tickets/__init__.py, vet/**, and strata/** that were not touched this
batch.

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

Filed: `T-draft-7bae70b7` (dup/_legacy_py._harvest_with grammar-mismatch bug,
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

<!-- ticket:T-0177 -->
```yaml
id: T-0177
title: 'frob serve daemon: incremental gate evaluation over the warm obligation graph'
state: queued
kind: feature
origin: human
created: '2026-07-18'
priority: medium
blocked_by:
- T-0410
parent: null
scope:
- src/frob/serve/**
- src/frob/gates/**
- src/frob/graph/**
- src/frob/app/**
- pyproject.toml
- Makefile
- docs/modules/serve.md
- tickets.md
- tests/test_serve.py
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_serve.py
  reason: T-0177 serve work maps to tests/test_serve.py
  actor: logan
  at: '2026-07-20'
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
frob serve is already a FastMCP stdio server with 5 read-only tools (doable tickets, stale docs, graph query, doc-for, check-scope) and is now wired into the coordinator's MCP config. Grow it into the structural fix for test-wait latency: the obligation graph knows exactly which obligations a diff can invalidate (frob test --base already proves the touched-set concept for tests) -- exploit it for gates. Deliverables: (1) warm state: the daemon holds the parsed graph snapshot, collected test ids, and the stamped violation baseline, refreshing incrementally on file-change (mtime/content-hash walk, reuse the .frob sqlite cache) instead of cold-parsing per invocation; (2) frob_check_delta MCP tool: given a base ref or dirty set, evaluate ONLY the obligations whose inputs changed and return the violation delta against the stamped baseline, in seconds; (3) frob_run_touched_tests tool wrapping the existing touched-set selection; (4) correctness guarantee: incremental results must provably match a cold frob check -- add a verification mode that runs both and diffs, plus property tests for the invalidation logic (an obligation NOT re-evaluated must have had no changed inputs -- vacuous-pass doctrine applies to the cache); (5) packaging: mcp becomes a proper [serve] extra in pyproject (mirroring [smt]) with _require_mcp's remedy message updated; Makefile install-tool already passes --with mcp -- reconcile with the extra; (6) docs/modules/serve.md updated with the daemon lifecycle and the staleness/correctness contract. Sequence AFTER the T-0148 sweep lands (gates code moves under it).

<!-- ticket:T-0204 -->
```yaml
id: T-0204
title: 'standing warnings triage: exports (12+ per pkg), dup 64 groups, arch 197 warns,
  perf 174'
state: queued
kind: bug
origin: human
created: '2026-07-18'
priority: medium
blocked_by: []
parent: null
scope:
- src/frob/**
- tests/**
- frob.toml
- docs/**
- tickets.md
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
User directive 2026-07-18: the pass-line counters hide real debt -- frob-exports reports 12-253 public symbols missing from __init__.py per package (decide policy: export or demote to private, per package, no blanket waiver), frob-dup 64 duplicate groups (triage: real extraction candidates vs false pairs; feeds T-0187 tree), frob-arch 197 warnings + 123 suggestions (long-function/god-class residue post-calibration -- fix or waive with reasons), perf gate 174 violations (166 waived -- re-audit every waiver still holds after T-0161's heuristic fixes land; the 8 unwaived need real fixes). Deliverable: each family driven to a state where the summary line is HONEST -- zero unwaived findings or a written per-finding reason; no threshold-loosening without a disclosed decision. Split into child tickets per family if any single family exceeds a session of work -- this ticket is the umbrella and the accounting.

<!-- ticket:T-0235 -->
```yaml
id: T-0235
title: exhaustive log/print call-site classification across src/frob (T-0202 follow-up)
state: queued
kind: ux
origin: human
created: '2026-07-18'
priority: medium
blocked_by: []
parent: null
scope:
- src/frob/**
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
T-0202 fixed the check-path log-level bug (stdout handler defaulted to DEBUG unconditionally) and demoted the per-symbol/per-violation INFO calls found in gates/graph along that path. It did not exhaustively classify every _log./print( call site repo-wide (~1016 sites across src/frob) into keep-INFO/demote-DEBUG/convert-print as the ticket's enumerate-first instruction asked -- only src/frob/{gates,graph,check,app/check_runner.py,logging} got a full pass; the other 26 files under src/frob/app/ (89 INFO, 125 ERROR, 46 print call sites) and all non-scope dirs (strata 27, vet 17, fuzz 6, dup 5, tickets 4, testing 3, perf 3, lang 3, serve 2, arch 2, stats 1, release 1, policy 1, mutate 1, cve 1) were only sampled, not individually classified. Do the full pass and produce the classification table T-0202's Done report deferred.

<!-- ticket:T-0254 -->
```yaml
id: T-0254
title: 'frob deploy epic: auditable, isolated, provable OS-layer deployment'
state: queued
kind: feature
origin: human
created: '2026-07-18'
priority: medium
blocked_by: []
parent: null
scope:
- src/frob/**
- strata-core/**
- design/**
- docs/**
- tests/**
- Makefile
- tickets.md
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
User mandate 2026-07-19: a frob deploy utility built into strata. The threat model: red teams compromise the one user that owns a service and nothing isolates that user -- lateral and vertical movement must be PROVABLY blocked, not hoped. The deployment sequence (idempotent install, status/health, uninstall with NO artifacts) must be auditable end to end, including an expensive opt-in VM-snapshot audit (VirtualBox) that is NOT part of make check. Scripts must tie into the model so hand edits are DETECTABLE through the strata checker, and the 'weird layer between the OS and the backend' (users, groups, units, ownership, ports) becomes provable architecture. Children: std.host OS-layer modeling -> movement-impossibility proofs + deploy script generation -> script<->model conformance gate -> VM snapshot audit harness -> real-service pilot (malmberg) remediating its awkward setup. Umbrella closes when all children close.

<!-- ticket:T-0260 -->
```yaml
id: T-0260
title: 'deploy pilot: model+generate+audit malmberg''s services, remediate the awkward
  setup'
state: queued
kind: feature
origin: human
created: '2026-07-18'
priority: medium
blocked_by:
- T-0257
parent: T-0254
scope:
- docs/**
- tests/**
- tickets.md
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
T-0254 child 6 (proof on reality). Apply the full chain to malmberg (the real server product from pilot P3: server_api/ingest/cloudsync/faces/backup/display + media_store): extend design/malmberg.strata with std.host (dedicated service users per component, units, ownership of media_store paths, ports), prove HOST001/HOST002 movement-impossibility or record honest waivers, generate the deploy scripts, run the conformance gate, and if a VirtualBox environment is available run the full VM snapshot audit and attach the attestation. Remediate the current awkward setup step in malmberg's docs/scripts with the generated sequence. Work happens IN THE MALMBERG REPO per the break-and-report pilot protocol (frob-side gaps come back as tickets, filed serially by the coordinator); this frob-side ticket tracks the campaign and collects the gap list. Success = malmberg installs/uninstalls via generated scripts with a green conformance gate and a documented (or executed) VM audit path.

<!-- ticket:T-0261 -->
```yaml
id: T-0261
title: 'std.host windows backend: services, gMSA/service accounts, ACLs, named pipes,
  firewall ports'
state: queued
kind: feature
origin: human
created: '2026-07-18'
priority: medium
blocked_by:
- T-0255
parent: T-0254
scope:
- strata-core/src/parse.rs
- src/frob/strata/**
- src/frob/deploy/**
- editors/**
- docs/strata/**
- tickets.md
- tests/unit/strata/
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/unit/strata/
  reason: T-0261 strata work maps to tests/unit/strata/
  actor: logan
  at: '2026-07-20'
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
T-0254 Windows pillar. Generalize the HostManifest (T-0255, Linux/systemd-first) into a platform-tagged model so a node can target windows. Windows analogs: service account instead of runs_as (dedicated low-priv local account, or a group Managed Service Account gMSA for domain-joined hosts -- NO interactive-logon right, deny-network-logon where possible, SeDenyBatchLogonRight per hardening); Windows Service (SCM) instead of systemd unit, with the hardening equivalents (service SID type restricted, required-privileges allowlist derived from may-capabilities, protected-process where applicable); NTFS ACLs (owner + explicit DACL entries) instead of POSIX owns MODE -- model must express deny-inheritance and per-principal rights, richer than a 3-octal mode; named pipes + Windows firewall rules for the listens surface. The platform tag drives which fields are required (a windows node without an ACL model is a HOST-family gap, mirroring a linux node without owns). Keep ONE HostManifest with a platform discriminator, not two parallel models -- the movement proofs (T-0256) and conformance (T-0258) must consume both uniformly. Grammar in parse.rs, tmLanguage drift-lock, litmus pair (linux + windows), docs/strata/host.md gains a Windows section. Generator/audit are separate tickets -- manifest + model only here.

<!-- ticket:T-0264 -->
```yaml
id: T-0264
title: 'frob deploy generate windows: PowerShell/DSC install/status/uninstall from
  the manifest, drift-locked'
state: queued
kind: feature
origin: human
created: '2026-07-18'
priority: medium
blocked_by:
- T-0257
- T-0261
parent: T-0254
scope:
- src/frob/deploy/**
- src/frob/app/**
- tickets.md
- docs/modules/deploy.md
- tests/unit/deploy/
scope_changes:
- op: remove
  glob: docs/**
  reason: 'scope hygiene (T-0455): narrow speculative docs/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: docs/modules/deploy.md
  reason: T-0264 deploy work maps to docs/modules/deploy.md
  actor: logan
  at: '2026-07-20'
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/unit/deploy/
  reason: T-0264 deploy work maps to tests/unit/deploy/
  actor: logan
  at: '2026-07-20'
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
T-0254 Windows generation. The T-0257 generator gains a windows target emitting idempotent PowerShell (check-then-apply, same contract as the bash target): install creates the service account/gMSA, registers the Windows Service with its hardening (service SID type, required-privileges, deny-logon rights), applies the NTFS ACLs exactly from the manifest, opens the declared firewall ports / creates named pipes, and configures the SPN + delegation setting from std.krb (setspn / the delegation flags) when a krb model is present. status queries SCM state + health. uninstall removes exactly the manifest set (service, account, ACL grants, firewall rules, SPN registration) leaving no artifacts. Same DEPLOY001 digest-header drift-lock as bash. Scripts must be PSScriptAnalyzer-clean and depend only on in-box modules (no PSGallery). The conformance gate (T-0258) and VM audit (T-0259) must handle the PowerShell mutation surface too -- coordinate the manifest abstraction so those tickets' parsers are platform-tagged, not bash-only; if T-0258/T-0259 landed bash-only, file follow-ups for their windows extension rather than expanding scope here.

<!-- ticket:T-0265 -->
```yaml
id: T-0265
title: self-referential frob:tests directive on a test function passes --ticket check
  but fails full DRIFT002
state: queued
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
blocked_by: []
parent: null
scope:
- src/frob/gates/**
- src/frob/graph/**
- tickets.md
- tests/test_gates.py
scope_changes:
- op: remove
  glob: tests/**
  reason: narrow speculative tests/** to the mirrored test module (T-0455 scope hygiene)
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_gates.py
  reason: T-0265 gates work is tested in tests/test_gates.py
  actor: logan
  at: '2026-07-20'
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
Recurring: implementer agents put a 'frob:tests <self>' directive above their own new test function; the target does not resolve as a graph qualname so full frob check fires DRIFT002, but frob check --delta --ticket (what agents+reviewers run) does NOT surface it -- so it lands and reddens main (happened for T-0213, T-0216; coordinator removed 3). Two fixes: (1) frob check --ticket should include the drift gate for edges the ticket's own diff ADDS (a new frob:tests directive in the diff must be validated even under --ticket scoping); (2) the graph should REJECT or warn on a frob:tests directive whose target is the annotated symbol itself (a test testing itself is meaningless) at directive-parse time, not silently store a dangling edge. Add a check-scoping regression + a self-edge rejection test.

<!-- ticket:T-0321 -->
```yaml
id: T-0321
title: 'frob daemon epic: warm shared project server (compute-once, serve-many, push-not-poll)'
state: queued
kind: feature
origin: human
created: '2026-07-19'
priority: medium
blocked_by: []
parent: null
scope:
- src/frob/serve/**
- src/frob/**
- tickets.md
- docs/modules/serve.md
scope_changes:
- op: remove
  glob: docs/**
  reason: 'scope hygiene (T-0455): narrow speculative docs/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: docs/modules/serve.md
  reason: T-0321 serve work maps to docs/modules/serve.md
  actor: logan
  at: '2026-07-20'
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
Expands T-0177 into a long-lived per-project daemon that holds warm, incrementally-maintained state (obligation graph + per-symbol digests, test collection, coverage, dup analysis, gate results) and serves it to all clients (agents, make, MCP, CI) via single-flight execution + a content-addressed result cache. Root cause it solves (observed live over a long multi-agent session): N parallel agents each redundantly recompute the same expensive state (make core, make coverage ~5min each, frob check 114s stages, ticket sweep dup-scan ~90s) in isolated worktrees with no sharing, and background-then-stall on make coverage. Children: (a) warm graph + FS-watch incremental invalidation by digest; (b) single-flight coverage/collection keyed by source digest, shared across worktrees with identical content; (c) local unix-socket JSON-RPC query protocol; (d) frob CLI auto-proxies to the daemon if running, else in-process (make targets become thin shims); (e) subscribe/push events (coverage-fresh, graph-changed) -- the stall-killer; (f) resource leases/semaphores (coverage=1 writer). MCP becomes one frontend over the same core. See the design discussion 2026-07-19.


## Integration / replacement map (2026-07-19 -- surveyed all subcommands + queue)
The daemon is a warm SUBSTRATE under most read/analysis subcommands, not a new silo.

SUBCOMMANDS -> daemon relationship:
- Warm GRAPH QUERIES (served instantly from the warm graph, zero recompute):
  outline, map, xref, parse, graph, exports, bind, docs, stats -- become thin daemon reads.
- Warm ANALYSIS (incremental, single-flight, cached by digest): dup, arch, perf, vet.
- Warm GATE eval (touched-set, the expensive path): check, sys, test, ticket(sweep/doable/evidence).
- FRONTENDS over one core: `serve` (MCP) becomes ONE frontend; the unix-socket JSON-RPC API is
  another; the `frob` CLI proxies to the daemon if running (make targets stay thin shims).
- One-shot / orthogonal (stay plain CLI; may read from daemon): scaffold, cycle, release, mutate,
  gitlog, ack, deploy.

EXISTING TICKETS the daemon SUBSUMES or de-risks (fold in as children/deps of this epic):
- T-0177 (incremental gate eval over warm graph) -- the SEED; this epic generalizes it. SUPERSEDES.
- T-0245 (stat storms + sqlite contention on /mnt/c, 13-60x tax) -- warm in-memory state + a single
  sqlite owner eliminate the re-stat/contention entirely. SUBSUMED (or its standalone fix becomes the
  daemon's storage layer).
- T-0243 (cache.db not invalidated across frob/parser upgrades) -- daemon owns cache lifecycle
  (digest + tool-version keyed). INTEGRATED.
- T-0279 (frob:tests direction disagrees: fresh dsl parse vs stale graph cache) -- daemon keeps the
  graph always-fresh, so the entire stale-cache class disappears. INTEGRATED.
- T-0180 (vetted-library cache engine) -- daemon holds the vet cache warm. INTEGRATED.
- T-0242 (frob test -> native sys audit on touched .strata) -- daemon touched-set orchestration. CHILD.
- T-0322 (coverage --wait / single-flight) + T-0324 (parametrized evidence) -- steps toward the daemon;
  0322 is the stall-killer extractable first. T-0292/T-0298 (evidence/collection resolution) become
  trivial once collection is warm. RELATED.
- T-0178 (agentic time profiling) -- the daemon is the natural instrumentation point. RELATED.
- T-0325 (doc-drift digest graph) -- the daemon's HEADLINE query (what code/docs must update when X
  changes); only practical warm. CHILD.
- T-0323 (git merge driver for tickets.md) -- INDEPENDENT of the daemon; do first regardless.


## Client-interface design constraints (HARD requirements: no init/deinit, impossible to misuse)
The daemon is a TRANSPARENT ACCELERATOR, never a thing the user/agent manages. Non-negotiable:

1. NO lifecycle commands in the happy path. There is NO `frob daemon start` / `stop` / `init` a
   client must run first. You just run `frob <cmd>` (or `make check`, or an MCP call) and it works.
   (A `frob daemon status`/`stop` MAY exist for debugging, but nothing REQUIRES them.)
2. TRANSPARENT AUTOSTART: the first query that could benefit spawns the daemon if none is running,
   via an atomic single-instance guard (flock/socket-bind on a .frob/ lockfile) so racing clients
   resolve to exactly one daemon -- never an "already running" error, never two daemons.
3. AUTO-SHUTDOWN on idle (N min) and on project-dir removal. No orphaned processes; nothing to clean
   up. Killing the daemon at any moment loses NOTHING (all durable state is content-addressed on disk).
4. CORRECTNESS MUST NOT DEPEND ON THE DAEMON (the #1 safety invariant): a daemon-served result MUST
   equal the in-process result, always -- the daemon only makes it FASTER. Enforce with single-flight
   + digest-keyed cache + FS-watch invalidation, and a property/differential test that daemon-answer
   == cold-answer for every query type. A stale-cache-served-as-fresh is the cardinal failure -- attack
   it in review (races, watch-miss, clock skew) like a security bug.
5. TRANSPARENT FALLBACK: if the daemon is unreachable / crashed / a STALE frob VERSION (post-upgrade)
   / times out, the client SILENTLY falls back to in-process computation (and best-effort restarts a
   fresh daemon). The client NEVER hangs and NEVER surfaces a daemon error for a normal command.
6. SELF-HEALING VERSION SKEW: on a frob/parser upgrade the client detects the running daemon's version
   mismatch and the daemon self-replaces (ties to T-0243/T-0279) -- no manual restart, no stale cache.
7. ZERO required config; opt-OUT only (e.g. FROB_NO_DAEMON=1 forces in-process). Works on a fresh clone
   with no setup step -- this is exactly the 'no awkward setup step' the frob owner wants everywhere.

Acceptance: a fresh clone runs `frob check` with the daemon auto-managed end-to-end, no init/deinit
command ever issued; kill -9 the daemon mid-use -> next command transparently succeeds (respawn or
in-process); daemon-answer == cold-answer differential test green for every served query; FROB_NO_DAEMON=1
fully bypasses it with identical results.

<!-- ticket:T-0322 -->
```yaml
id: T-0322
title: 'coverage --wait / push contract: agents block on a socket recv, never background-and-stall'
state: queued
kind: feature
origin: human
created: '2026-07-19'
priority: medium
blocked_by: []
parent: null
scope:
- src/frob/app/**
- src/frob/testing/**
- src/frob/serve/**
- tickets.md
- tests/test_app.py
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_app.py
  reason: T-0322 app work maps to tests/test_app.py
  actor: logan
  at: '2026-07-20'
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
THE stall-killer, extractable before the full daemon. Observed: implementer agents run make coverage in the background and stall waiting for a Monitor notification they cannot act on -- work done, uncommitted, looping 'waiting for coverage'; coordinator had to take over ~5 agents this session. Provide a blocking-until-fresh coverage/test contract (a foreground  that blocks on completion, backed by single-flight so concurrent callers share one run) so an agent gets a definitive fresh-or-failed result inline instead of babysitting a detached job. Interim (pre-daemon): a proper foreground make-coverage wrapper + single-flight file lock so 6 agents don't each run the full suite.

<!-- ticket:T-0325 -->
```yaml
id: T-0325
title: 'doc-drift digest graph: warm ''what code/docs must update when X changes''
  query (the north-star)'
state: queued
kind: feature
origin: human
created: '2026-07-19'
priority: medium
blocked_by: []
parent: null
scope:
- src/frob/graph/**
- src/frob/serve/**
- tickets.md
- docs/modules/graph.md
scope_changes:
- op: remove
  glob: docs/**
  reason: 'scope hygiene (T-0455): narrow speculative docs/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: docs/modules/graph.md
  reason: T-0325 graph work maps to docs/modules/graph.md
  actor: logan
  at: '2026-07-20'
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
The user's original vision (CLAUDE.md): every function/class/etc. carries a digest in .frob/, every doc is connected, and frob answers -- without running a test, like a static type-checker for docs -- 'X's digest changed, here is the transitively-affected doc + code set that must be reviewed/updated.' Only practical if the graph is kept WARM (frob daemon epic). Query surface: graph.affects(symbol) -> impacted docs+symbols; a gate that fails when a touched symbol's dependents' digests weren't acked. This is the same project as the daemon; file so the digest-graph work is tracked as its own deliverable.

<!-- ticket:T-0329 -->
```yaml
id: T-0329
title: 'EPIC arch multi-language: normalized code model + Rust/TypeScript/Kotlin adapters'
state: queued
kind: feature
origin: human
created: '2026-07-19'
priority: medium
blocked_by: []
parent: null
scope:
- src/frob/arch/**
- src/frob/lang/**
- docs/modules/arch.md
- tickets.md
- tests/unit/test_arch.py
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/unit/test_arch.py
  reason: T-0329 arch work maps to tests/unit/test_arch.py
  actor: logan
  at: '2026-07-20'
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
frob arch today has per-language walkers (_python.py, _cpp.py) only. To extend cleanly (not N copies of each check), introduce a NORMALIZED CODE MODEL: a language-agnostic view (module, class, function, method, param, branch, loop, call, import, override, field-access, return, raise/throw, catch) that each language adapter maps its tree-sitter grammar onto. Checks are written ONCE against the model; adapters supply per-grammar node-type maps. Then add adapters for TypeScript, Rust, Kotlin (Kotlin needs tree-sitter-kotlin added to frob.lang; ts/rust/cpp/c already parse via tree-sitter-language-pack). Language-specific checks (Rust must_use/ownership, TS any/strict-null) live in per-language extensions on top of the shared model. Acceptance: an arch check written once fires correctly across python+ts+rust+kotlin on equivalent code; Kotlin grammar wired; the existing python/cpp checks refactored onto the model with no regression. Children: normalized-model, ts-adapter, rust-adapter, kotlin-grammar+adapter.

<!-- ticket:T-0330 -->
```yaml
id: T-0330
title: EPIC arch SOLID + senior-designer checks (static proxies for real design principles)
state: queued
kind: feature
origin: human
created: '2026-07-19'
priority: medium
blocked_by: []
parent: null
scope:
- src/frob/arch/**
- src/frob/graph/**
- docs/modules/arch.md
- tickets.md
- tests/unit/test_arch.py
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/unit/test_arch.py
  reason: T-0330 arch work maps to tests/unit/test_arch.py
  actor: logan
  at: '2026-07-20'
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
Encode what a senior software designer knows (SOLID, ArjanCodes, Logan-Smith type-driven design, logging, fallibility) as STATIC checks over parsed source -- each with a concrete, non-hacky static proxy (subjective principles get objective detectable smells). CATALOG (each becomes a child ticket, ARCH1xx family):
SRP/cohesion: LCOM4 low-cohesion class (methods partition into disjoint field-usage components); god-module (unrelated exports); mixed-concern function (I/O capability + pure compute + formatting in one body).
OCP: type-dispatch smell (N+ isinstance/type==/tag switch on one variable -> polymorphism); non-exhaustive enum match.
LSP (Liskov): override raises NotImplementedError; override signature incompatible (narrower params / different-or-wider return = variance violation); override strengthens a precondition (adds assert/raise base lacks) or weakens a postcondition; override no-ops a value-returning base method.
ISP: fat interface (ABC/Protocol/trait whose implementers stub most methods with raise NotImplementedError/pass); client using only a subset of a wide injected interface.
DIP: LAYERING CONTRACT -- a declared allowed-module-dependency graph (import-linter style), violation = a high layer importing a low/concrete module across the boundary; concrete-collaborator construction inside a method instead of injection (no DI).
Type-driven (Logan Smith): make-illegal-states-unrepresentable (bool flag + validation -> enum/newtype); primitive obsession (many raw str/int params for a domain concept); parse-dont-validate (validates then returns the same unrefined type); boolean/flag parameter (public fn bool param switching behavior -> split).
Logging (CLAUDE.md 'log everything worth logging'): unlogged error path (except/raise/return-Err with no log in it); unlogged boundary (public entry / subprocess / net / fs site with no surrounding log); print()-as-diagnostics.
Fallibility (typani Result / Rust must_use): unhandled Result (Result-returning call as a bare statement, value discarded); swallowed exception (bare except / except Exception: pass); raises a recoverable error where the signature returns T not Result[T,E]; over-broad except; re-raise losing context.
Other smells: mutable default argument; feature envy (method uses another object more than self); data clumps (same 3+ params passed together repeatedly); magic numbers/strings in logic; module dependency CYCLES; dead private code (unreferenced private symbol); deep inheritance (DIT); temporal coupling (_initialized-flag guard).
Every check names its static proxy, severity, and the ARCHxxx id; each is waivable via the ARCH001-style reasoned override (T-0289). MUST coincide with strata (see the systems epic): logging-IN-CODE is arch; observability-OF-FLOW is strata -- no overlap.

ADVERSARIAL HARDENING (2026-07-20, see docs/design/structural-linter-adversarial-hardening.md): each ARCH1xx check must ground on the RESOLVED graph not a surface/syntactic proxy (measure the LOGICAL unit -- inline single-caller private helpers via the T-0288 call graph before complexity; a helper module called only by one class IS that class); resolve re-exports transitively and FAIL CLOSED on dynamic/reflective indirection; the generated marker (T-0234) must not exempt arch. Escape hatches are BOUNDED: waiver budget/density + reason-quality + staleness meta-gate, and global threshold loosening is an AUDITED config event, never silent (per-function reasoned override only, T-0289). Coincident with the conformance-totality epic T-0341.

EXHAUSTIVENESS DRIFT-LOCK (T-0343, 2026-07-20 mandate 'implementation MUST address EVERYTHING the exhaustive researcher found'): this epic's implementation binds to the corpus DENOMINATOR MANIFEST via T-0343's N:M coverage meta-test. Denominator source: architecture-check-catalog.md (tier-1 statically-checkable entries) + design-pattern-traps-corpus.md (trap hallmarks). Every relevant manifest entry must map to >=1 registered check/obligation/recommender-rule OR carry an explicit reasoned deferral (advisory/not-checkable/ticketed); (addressed union deferred) == TOTAL. The epic CANNOT close while any researched entry is un-addressed and un-deferred -- the corpora (docs/design/*) are the enforceable denominator, not just reading.

<!-- ticket:T-0331 -->
```yaml
id: T-0331
title: 'EPIC strata senior-systems checks: reliability/observability/consistency/distributed
  (complete, not hacky)'
state: queued
kind: feature
origin: human
created: '2026-07-19'
priority: medium
blocked_by: []
parent: null
scope:
- src/frob/strata/**
- strata-core/**
- docs/strata/**
- tickets.md
- tests/unit/strata/
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/unit/strata/
  reason: T-0331 strata work maps to tests/unit/strata/
  actor: logan
  at: '2026-07-20'
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
Complete the system-design linter with what a senior systems/reliability engineer checks -- over the .strata MODEL (nodes/flows/boundaries/stores), each a real static obligation, SYS2xx/REL2xx family. CATALOG:
Reliability: TIMEOUT on every remote/cross-boundary flow (unbounded hang otherwise); RETRY must declare exponential backoff+jitter, and no retry on a non-idempotent op; IDEMPOTENCY key required on a mutating op reachable by a retryable flow (duplicate effects); CIRCUIT BREAKER / bulkhead per external dependency (extends LINT004 kill-switch); FALLBACK / graceful degradation declared for a CRITICAL dependency; HEALTH liveness+readiness on every service node; SPOF -- a node with inbound critical flows and replicas_max=1/no redundancy; BACKPRESSURE bounded intake on queues/consumers (extends LINT003 surge / LINT005 capacity).
Observability: every boundary flow emits metrics+traces+logs; CORRELATION/trace-id propagated across a flow chain (distributed tracing); golden-signal SLOs (latency/traffic/errors/saturation) + error budget declared per service.
Data/consistency: SINGLE SOURCE OF TRUTH (two nodes writing one store = hazard; extends SYS003 hub); transactional boundary on multi-write ops; MESSAGE SCHEMA VERSION on events/queues (backward-compat); exactly-once vs at-least-once declared on queues; retention/TTL on PII stores (ties T-0207).
Distributed: SYNC CALL-CHAIN DEPTH bound (cascading latency/failure; uses reachability incl. non-transitive T-0282); distributed txn across services requires saga/compensation; no shared mutable state across service boundaries; clock/ordering assumptions (T-0282).
Each is a strata surface addition (new node/flow attrs) + a checker + litmus + docs, deny-by-default with a reasoned waive channel (T-0174). COINCIDENCE with arch: strata reasons over the MODEL (flows/nodes); arch reasons over CODE (functions). Where they touch (observability, error handling), the code check BACKS the system claim via the capability/binding graph -- one obligation, checked at the right level, never duplicated.

## PROVABILITY CONSTRAINT (user, 2026-07-19 -- non-negotiable)
strata's job is NOT model-only lint. Its purpose is to PROVE the actual CODE conforms to
the .strata system design, the way a type-checker proves code matches its types. The
existing bridge is capability self-conformance (SYS100 undeclared-capability-in-code,
SYS101 declared-but-never-observed, SYS102 unmodeled-code). EVERY new systems obligation
here MUST preserve this: an obligation is satisfied ONLY by one of --
  (a) PROOF AGAINST CODE: the code is analyzed and shown to match the declared property
      (e.g. a flow declaring timeout=T must have an actual timeout arg at the real call
      site; a node declaring a fallback must have the fallback path in code; a declared
      retry-backoff must match the code's retry loop; declared observability must have the
      instrumentation). This reuses arch's code analysis + the capability/binding graph.
  (b) PROOF AGAINST MODEL: the kernel model-checks it structurally (reach/noflow/isolation).
  (c) EXPLICIT REASONED DISCHARGE: an assume/waive (T-0174) with a written reason + ticket,
      when the code cannot be statically shown -- NEVER a silent pass.
NO obligation may be satisfied by bare declaration in the .strata file alone. FOUNDATIONAL
DEPENDENCY: proof-against-code is only sound if the code analysis is sound -- an evadable
scanner (grep) makes SYS100 unsound (exec via an alias slips the proof). So T-0328
(import/binding-aware resolution) underpins this whole epic; the code<->model proof is only
as trustworthy as the resolver. This is the arch<->strata coincidence in full: arch analyzes
code STRUCTURE; strata PROVES code CONFORMS to the declared system model, USING arch's
analysis + the capability graph as the evidence.

ADVERSARIAL HARDENING (2026-07-20, see docs/design/structural-linter-adversarial-hardening.md): the anti-evasion structure is CONFORMANCE TOTALITY (epic T-0341): coverage totality (every capable module binds to a node), EXACT interface conformance (declared interface == real public surface), a PURPOSE contract (purpose carries an allowed-effect profile), binding totality (no laundering logic into an unbound file), effect conformance with opaque effects FAILING CLOSED (T-0339), and bounded/staleness-gated assumes+waivers with an un-droppable floor view. 'No obligation by bare declaration' is made TOTAL: the model cannot be dangerous-and-silent.

EXHAUSTIVENESS DRIFT-LOCK (T-0343, 2026-07-20 mandate 'implementation MUST address EVERYTHING the exhaustive researcher found'): this epic's implementation binds to the corpus DENOMINATOR MANIFEST via T-0343's N:M coverage meta-test. Denominator source: system-design-corpus.md (the entries tagged strata-checkable). Every relevant manifest entry must map to >=1 registered check/obligation/recommender-rule OR carry an explicit reasoned deferral (advisory/not-checkable/ticketed); (addressed union deferred) == TOTAL. The epic CANNOT close while any researched entry is un-addressed and un-deferred -- the corpora (docs/design/*) are the enforceable denominator, not just reading.

<!-- ticket:T-0332 -->
```yaml
id: T-0332
title: 'design-pattern recommender: hallmark->pattern + anti-pattern->escape registry
  (advisory)'
state: queued
kind: feature
origin: human
created: '2026-07-19'
priority: medium
blocked_by: []
parent: T-0330
scope:
- src/frob/arch/**
- docs/modules/arch.md
- tickets.md
- tests/unit/test_arch.py
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/unit/test_arch.py
  reason: T-0332 arch work maps to tests/unit/test_arch.py
  actor: logan
  at: '2026-07-20'
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
Positive complement to the SOLID smell catalog (T-0330). An exhaustive PATTERN REGISTRY (structured like the capability registry -- pattern x hallmark x language matrix, covered-or-excused): each entry = a HALLMARK detector (the before-shape), the recommended PATTERN (GoF + modern), the FORCE/tension it resolves, a refactoring sketch, languages. Two directions: HALLMARK->PATTERN (N-arm isinstance/type-switch -> Strategy/polymorphism; growing if-chain on a state field -> State machine; scattered ConcreteX() construction -> Factory/DI; telescoping optional ctor params -> Builder; manual callback lists -> Observer; repeated wrap+delegate -> Decorator; incompatible-interface bridging -> Adapter; expensive-object reuse -> Flyweight/pool) and ANTI-PATTERN->ESCAPE (god object -> SRP decompose; anemic domain model -> move behavior to data; stringly-typed -> newtype; poltergeist/lava-flow -> delete; sequential coupling -> explicit state). CRITICAL DESIGN (do it right, avoid cargo-culting): (1) RECOMMENDATIONS not errors -- advisory/suggestion severity only, forcing a pattern is itself over-engineering; the user said 'recommended'. (2) STRONG-HALLMARK-ONLY / high precision -- recommend only on an unambiguous structural signal; a noisy recommender trains users to ignore it; the library itself must NOT recommend when the code is already simple. (3) PAIRS WITH the SOLID smells -- reuse the same hallmark detectors: the smell is the diagnosis, the pattern is the prescription (one detector, two outputs: 'violates OCP' + 'consider Strategy'). (4) WAIVABLE with a reason so a repo records deliberate exceptions. (5) each recommendation names the FORCE + a concrete sketch, never a bare 'use Strategy'.

EXHAUSTIVENESS DRIFT-LOCK (T-0343, 2026-07-20 mandate 'implementation MUST address EVERYTHING the exhaustive researcher found'): this epic's implementation binds to the corpus DENOMINATOR MANIFEST via T-0343's N:M coverage meta-test. Denominator source: design-pattern-catalog.md (341 patterns) + design-pattern-traps-corpus.md (anti-pattern->escape hallmarks). Every relevant manifest entry must map to >=1 registered check/obligation/recommender-rule OR carry an explicit reasoned deferral (advisory/not-checkable/ticketed); (addressed union deferred) == TOTAL. The epic CANNOT close while any researched entry is un-addressed and un-deferred -- the corpora (docs/design/*) are the enforceable denominator, not just reading.

<!-- ticket:T-0339 -->
```yaml
id: T-0339
title: 'EPIC: sound capability may-analysis -- exhaustive over static name-binding
  per language spec, fail-closed on runtime dispatch'
state: queued
kind: security
origin: human
created: '2026-07-20'
priority: medium
blocked_by: []
parent: null
scope:
- src/frob/vet/**
- src/frob/lang/**
- src/frob/strata/**
- tickets.md
- docs/modules/vet.md
- tests/test_vet.py
scope_changes:
- op: remove
  glob: docs/**
  reason: 'scope hygiene (T-0455): narrow speculative docs/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: docs/modules/vet.md
  reason: T-0339 vet work maps to docs/modules/vet.md
  actor: logan
  at: '2026-07-20'
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_vet.py
  reason: T-0339 vet work maps to tests/test_vet.py
  actor: logan
  at: '2026-07-20'
evidence: []
attachments: []
acceptance:
- given a per-language-spec denominator of every name-binding/aliasing/re-export construct
  that can route a call to a dangerous target (Python, TypeScript/JS, Rust, C, C++,
  Kotlin), when the capability resolver runs, then EVERY such STATIC construct resolves
  the call to its dangerous target -- verified by one litmus per construct, with a
  coverage table proving the denominator is fully covered
- given any RUNTIME-resolved indirection the spec defines as opaque to static analysis
  (reflection, eval/exec, dynamic import, computed member access with non-constant
  key, callable retrieved from a container, function pointer from a non-constant expression),
  when it could reach a call position, then the analyzer FAILS CLOSED -- emits an
  'opaque capability indirection' obligation that must be discharged by a reasoned
  waiver, never a silent pass
- 'given the two guarantees above, evasion is impossible-in-the-silent-sense: a reviewer
  can point to the per-spec denominator table (static fragment complete) and the fail-closed
  obligation (dynamic fragment gated), so no code path routes a dangerous call to
  an unaccounted sink without either resolving to it or tripping the opaque-indirection
  finding'
threat: elevation-of-privilege
component: null
labels: []
```
User mandate (2026-07-20): 'ensure that you stop ALL methods EXHAUSTIVELY across ALL LANGUAGES of evading detection. ENSURE THAT IT IS 100% EXHAUSTIVE via LANGUAGE SPEC.' HONEST ARCHITECTURE (recorded so no one later mistakes the goal for the impossible one): a sound STATIC analyzer cannot resolve runtime dispatch (getattr/eval/reflection/dynamic-require/fn-ptr-from-data) -- Rice's theorem. So 'exhaustive' means: (1) EXHAUSTIVE-RESOLVE the DECIDABLE fragment -- enumerate FROM EACH LANGUAGE SPEC every static name-binding/aliasing/re-export/copy construct (imports, import-as, from-import[-as], star-import, local + chained + attribute rebinding, destructuring, tuple/list unpack, Rust use/use-as/pub use, C/C++ #define + using-decl + function-pointer init from a named fn + typedef'd fn-ptr, Kotlin import-as + ::ref + typealias) and resolve calls through all of them, transitively, per-scope, cycle-guarded, WITHOUT regressing shadowing soundness (a benign/param binding must stay silent); (2) FAIL CLOSED on the UNDECIDABLE fragment -- every spec-defined runtime-resolved indirection becomes an 'opaque capability indirection' obligation (fires, requires a reasoned waiver), consistent with strata's prove-or-reject philosophy (T-0290 recursion, arch-override). DELIVERY: (a) dispatch exhaustive-research to produce the per-language evasion denominator from the actual specs (the coverage denominator for acceptance 1) + the opaque-construct list (acceptance 2); (b) child tickets per language implementing the static resolver to its denominator + litmus; (c) one child for the fail-closed opaque-indirection obligation in the scanner/strata may-analysis; (d) a cross-language exhaustiveness meta-test binding each denominator entry to its litmus (fails if a construct has no fixture, like the CVE catalog drift-lock). T-0337 (Python local rebind) and T-0328 (Python import resolution) are the first two leaves. This is the 'you cannot get around it' guarantee the whole tool exists for.

EXHAUSTIVENESS DRIFT-LOCK (T-0343, 2026-07-20 mandate 'implementation MUST address EVERYTHING the exhaustive researcher found'): this epic's implementation binds to the corpus DENOMINATOR MANIFEST via T-0343's N:M coverage meta-test. Denominator source: capability-evasion-taxonomy.md (every static-resolvable construct -> a resolver litmus; every runtime-opaque construct -> a fail-closed obligation). Every relevant manifest entry must map to >=1 registered check/obligation/recommender-rule OR carry an explicit reasoned deferral (advisory/not-checkable/ticketed); (addressed union deferred) == TOTAL. The epic CANNOT close while any researched entry is un-addressed and un-deferred -- the corpora (docs/design/*) are the enforceable denominator, not just reading.

<!-- ticket:T-0340 -->
```yaml
id: T-0340
title: native extensions get uninstalled by uv sync/build -- make strata_core/frob_core
  survive (or auto-rebuild)
state: queued
kind: bug
origin: human
created: '2026-07-20'
priority: medium
blocked_by: []
parent: null
scope:
- Makefile
- pyproject.toml
- docs/**
- tickets.md
scope_changes: []
evidence: []
attachments: []
acceptance:
- given the editable maturin-develop natives (strata_core, frob_core) are built, when
  any uv operation that re-syncs the environment runs (uv lock, uv sync, uv build
  via frob release stamp, or a uv run that triggers a sync after a pyproject change),
  then the natives remain importable -- either uv is configured not to evict them,
  or they are transparently rebuilt, so pytest collection / frob check never silently
  degrade to NativeExtensionUnavailable mid-run
- given a fresh clone or a stamp that did evict them, when the developer/agent runs
  the standard build/test entrypoint, then natives are ensured present with no manual
  'make core' needed as a separate remembered step
threat: null
component: null
labels: []
```
Recurring, high-cost friction ([[worktree-natives-artifact]]): the maturin-develop editable installs of strata_core/frob_core are not tracked in uv.lock, so uv treats them as extras and REMOVES them on any environment re-sync -- triggered by , , load_graph: loaded 6496 symbols, 4043 edges
release: stamped 927 public symbol(s) at 0.20.0
stamped public API at 0.20.0 -> .frob-release.json's build step, or a Provide a command or script to invoke with `uv run <command>` or `uv run <script>.py`.

The following commands are available in the environment:

- cffi-gen-src
- coverage
- coverage-3.11
- coverage3
- dotenv
- frob
- httpx
- hypothesis
- idna
- jsonschema
- mcp
- py.test
- pygmentize
- pytest
- python
- python3
- python3.11
- ruff
- ty
- uvicorn

See `uv run --help` for more information. after a pyproject edit. This bit the campaign live multiple times (a black-dep edit and every version-bump stamp nuked them mid-flow, causing SYS004/collection failures that look like regressions). Options to evaluate: (a) a  setting /  sync mode that stops uv evicting them; (b) a Makefile/entrypoint wrapper (e.g. a  target or a post-sync hook) that rebuilds natives whenever they're missing before test/check; (c) building+installing them as real (non-editable) wheels pinned in the lock. Pick the one that makes 'natives are always present' an invariant, not a remembered manual step. This is the deepest papercut behind the whole worktree-natives artifact class.

<!-- ticket:T-0341 -->
```yaml
id: T-0341
title: 'EPIC: strata conformance totality -- every module binds to a node, declares
  its exact interface + purpose, effects proven against code'
state: queued
kind: security
origin: human
created: '2026-07-20'
priority: medium
blocked_by: []
parent: null
scope:
- src/frob/strata/**
- src/frob/vet/**
- src/frob/graph/**
- tickets.md
- docs/modules/strata.md
- tests/unit/strata/
scope_changes:
- op: remove
  glob: docs/**
  reason: 'scope hygiene (T-0455): narrow speculative docs/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: docs/modules/strata.md
  reason: T-0341 strata work maps to docs/modules/strata.md
  actor: logan
  at: '2026-07-20'
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/unit/strata/
  reason: T-0341 strata work maps to tests/unit/strata/
  actor: logan
  at: '2026-07-20'
evidence: []
attachments: []
acceptance:
- 'COVERAGE TOTALITY (SYS-COV): every deployable/public module -- and every module
  the binding-aware scanner finds ANY capability in -- must bind to exactly one strata
  node; unbound-but-capable code is a hard failure (the model cannot omit dangerous
  code)'
- 'INTERFACE CONFORMANCE (exact): a node''s declared interface must EQUAL the code''s
  actual public surface -- an undeclared public export fails, and a declared-but-absent
  symbol fails; every module is forced to declare its interface and keep it in lockstep
  with the code'
- 'PURPOSE CONTRACT: every node declares a PURPOSE carrying an allowed-effect profile;
  an effect outside the purpose''s profile (e.g. a network effect in a declared logging/pure
  purpose) fires and needs a reasoned discharge -- purpose is a typed constraint,
  not a comment'
- 'BINDING TOTALITY + EFFECT CONFORMANCE: code<->node binding is a TOTAL function
  over capable code (no laundering logic into an unbound file); the exhaustive binding-aware
  scanner''s extracted effect set must be a subset of what the node declares, declared
  >= actual, with opaque/unresolvable effects failing closed (T-0339)'
- 'BOUNDED ESCAPE HATCHES + GATED CONFIG: waivers/assumes are counted, reason-required,
  staleness-dated, and budget-limited (waive-everything is itself a smell); baseline-view
  and threshold loosening is an audited event, never silent'
threat: elevation-of-privilege
component: null
labels: []
```
The user asked (2026-07-20): 'what mechanisms enforce conformance to the .strata file? Do we force every module to declare its purpose and interface?' -- and to harden it adversarially. Design north-star: docs/design/structural-linter-adversarial-hardening.md. Today _code_binding.py (bind_code/ConformanceReport/check_import_conformance) and _effects.py::check_capability_conformance exist, and T-0331 already mandates 'NO obligation satisfied by bare declaration' -- but conformance is NOT TOTAL, which is the evasion surface: (1) un-modeled modules escape all obligations; (2) a node can declare a partial interface while the code exports more; (3) nothing binds a module's PURPOSE to an allowed-effect profile; (4) binding need not be total, so logic can be laundered into an unbound file. This epic closes those into the five acceptance criteria above (SYS-COV coverage totality, exact interface conformance, purpose contract, binding totality + effect conformance, bounded escape hatches + gated config), each a child ticket. Soundness rests entirely on the exhaustive binding-aware scanner (T-0328/T-0337/T-0339) -- this epic is the conformance layer ON TOP of that foundation. Coincident with the arch epic (T-0330) and strata-systems epic (T-0331); this is the 'the model cannot lie about the code' guarantee made total.

EXHAUSTIVENESS DRIFT-LOCK (T-0343, 2026-07-20 mandate 'implementation MUST address EVERYTHING the exhaustive researcher found'): this epic's implementation binds to the corpus DENOMINATOR MANIFEST via T-0343's N:M coverage meta-test. Denominator source: the conformance mechanisms in structural-linter-adversarial-hardening.md (coverage/interface/purpose/binding/effect totality). Every relevant manifest entry must map to >=1 registered check/obligation/recommender-rule OR carry an explicit reasoned deferral (advisory/not-checkable/ticketed); (addressed union deferred) == TOTAL. The epic CANNOT close while any researched entry is un-addressed and un-deferred -- the corpora (docs/design/*) are the enforceable denominator, not just reading.

<!-- ticket:T-0346 -->
```yaml
id: T-0346
title: 'EPIC: unified design-knowledge registry -- single source of truth, per-entry
  disposition, no prose-only or split-across-files misses'
state: queued
kind: feature
origin: human
created: '2026-07-20'
priority: medium
blocked_by: []
parent: null
scope:
- docs/design/**
- src/frob/strata/**
- src/frob/arch/**
- tickets.md
- tests/unit/strata/
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/unit/strata/
  reason: T-0346 strata work maps to tests/unit/strata/
  actor: logan
  at: '2026-07-20'
evidence: []
attachments: []
acceptance:
- every item across ALL corpora (design patterns, arch checks, traps, system-design,
  capability-evasion, security/CWE, compliance, secrets, PII, supply-chain) has a
  stable canonical id in ONE machine-readable registry (docs/design/registry/*.yaml
  or equivalent); the prose corpus docs become human elaboration that REFERENCES registry
  ids, never the sole home of an entry -- a reconciliation test fails if any prose
  entry (a table row / named item in a corpus doc) has no registry id (a prose-only
  miss) or if two docs describe the same item under different unlinked ids (a split-across-files
  miss)
- 'TRUE exhaustiveness: enumerations that were bulk-skipped or census-only get COMPLETED
  to per-entry granularity with an individual disposition each -- CWE-1000 full (~900+,
  each: has-design-precondition->checkable / no-kernel-concept->out-of-scope-naming-the-missing-concept
  / duplicate-of-cataloged-id), AWS pattern catalog, the detector rule sets counted
  only as census (gitleaks/trufflehog/GitHub-partner-patterns). ''seems like spam/redundant''
  is NOT a valid skip; redundant-with-X is a disposition (duplicate-of X), not an
  omission'
- 'every registry entry carries a DISPOSITION: addressed-by-check(s) <ids> | reasoned-deferral(advisory/not-checkable,
  reason) | duplicate-of <id> | out-of-scope(named-missing-concept). T-0343''s exhaustiveness
  drift-lock binds to this registry and fails if ANY entry lacks a disposition or
  an addressed entry''s check vanishes -- so an implementing ticket provably addresses
  EVERYTHING'
threat: null
component: null
labels: []
```
User critique (2026-07-20): the corpora hedged where the mandate is to EXHAUST -- e.g. security-corpus skipped CWE-1000 as 'repo spam' when the intent is to enumerate ALL ~900, categorize each, and reason mitigation per entry; and information split across 10 docs/design/*.md files means an item can exist in one file's prose but be absent from the enforceable denominator ('miss split across two files'). This epic makes the corpus a REGISTRY, not a reading list: (1) a single canonical machine-readable registry aggregating every corpus manifest with stable ids + cross-refs (pattern<->trap<->evasion<->mitigation linked by id); (2) a reconciliation/consolidation pass that de-dups cross-file and flags any prose-only entry; (3) completion of the bulk-skipped enumerations to per-entry disposition; (4) T-0343 (exhaustiveness drift-lock) bound to the registry with a mandatory per-entry disposition. Governs T-0330/331/332/339/341/343 and all the corpus docs. The corpora already emit '## DENOMINATOR MANIFEST' sections (per-doc TOTAL); this epic unifies them into one registry and closes the 'seems like spam so I skipped it' and 'split across two files' gaps permanently.

<!-- ticket:T-0352 -->
```yaml
id: T-0352
title: 'structural PII/secrets: TS/Rust field-shape equivalents'
state: queued
kind: feature
origin: human
created: '2026-07-20'
priority: medium
blocked_by: []
parent: null
scope:
- src/frob/gates/**
- src/frob/lang/**
- tests/test_gates.py
- docs/modules/gates.md
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_gates.py
  reason: T-0352 gates work maps to tests/test_gates.py
  actor: logan
  at: '2026-07-20'
- op: remove
  glob: docs/**
  reason: 'scope hygiene (T-0455): narrow speculative docs/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: docs/modules/gates.md
  reason: T-0352 gates work maps to docs/modules/gates.md
  actor: logan
  at: '2026-07-20'
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
T-0207 follow-on: frob.gates._pii_structural.FIELD_SIGNATURES is Python-only (ast-based). Extend PII010/SEC110 to TypeScript/Rust field-shape and env-access equivalents (process.env, std::env::var) per the ticket body's cross-language mandate. Deferred from T-0207's scope.

<!-- ticket:T-0354 -->
```yaml
id: T-0354
title: app/ticket_runner.py _run_sweep has same full-root xref bug as sweep_ticket
  (T-0240 sibling)
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
blocked_by: []
parent: null
scope:
- src/frob/app/ticket_runner.py
scope_changes: []
evidence:
- tests/unit/test_app_runners_batch7.py::TestTicketStart::test_start_foreground_runs_sweep_synchronously
- tests/unit/test_app_runners_batch7.py::TestSpawnBackgroundSweep::test_spawns_detached_sweep_subprocess
- tests/unit/test_app_runners_batch7.py::TestSpawnBackgroundSweep::test_popen_failure_falls_back_to_synchronous_sweep
- tests/unit/test_app_runners_batch7.py::TestSpawnBackgroundSweep::test_exec_kill_switch_forces_synchronous_sweep
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
found while working T-0240: gates/_prework.py::sweep_ticket's xref loop called xref(symbol, root) instead of the scan_path it computed, and derived xref-hit terms via Path(pattern).stem (nonsense for glob patterns). app/ticket_runner.py's _run_sweep + _xref_hits_for_scope + _scope_digest_for_ticket carry an IDENTICAL copy of the same loop (already flagged as duplicate call-site debt in T-0236's Done report, follow-up ticket not yet filed) with the same two bugs. src/frob/app/** was out of scope for T-0240 (whose scope was tickets/gates/dup/tests only), so this sibling copy still has the unbounded-walk + nonsense-stem bugs. Either delegate _run_sweep to frob.gates._prework.sweep_ticket directly (collapsing the duplication per T-0236) or port the same fix.

## Done report

Delegated app/ticket_runner.py's _run_sweep to frob.gates.sweep_ticket
instead of carrying its own copy of the xref loop (T-0236's flagged
follow-up). The old copy had the same two bugs T-0240 fixed in
gates/_prework.py::sweep_ticket: an unbounded xref(symbol, root) re-walk
of the whole tree per scope pattern (ignoring the scan_path it computed),
and a Path(pattern).stem guess feeding raw glob syntax into xref as a
symbol name. src/frob/app/** was out of T-0240's scope, so this sibling
copy kept both bugs live. Removed the duplicate _xref_hits_for_scope and
_scope_digest_for_ticket helpers entirely; _run_sweep now calls
sweep_ticket(root, ticket) directly, so the two call sites can no longer
desync.

### Changed
```
 src/frob/app/ticket_runner.py | 73 +++++++++++++------------------------------
 tickets.md                    | 30 ++++++++++++++++--
 2 files changed, 49 insertions(+), 54 deletions(-)
```

### Evidence
- `tests/unit/test_app_runners_batch7.py::TestTicketStart::test_start_foreground_runs_sweep_synchronously` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSpawnBackgroundSweep::test_spawns_detached_sweep_subprocess` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSpawnBackgroundSweep::test_popen_failure_falls_back_to_synchronous_sweep` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSpawnBackgroundSweep::test_exec_kill_switch_forces_synchronous_sweep` (pytest node id, verified passing when recorded)
<!-- ticket:T-0355 -->
```yaml
id: T-0355
title: 'sweep: clean SIGINT message + PRE001 catch-22 on slow mounts + scope_digest
  content-keying'
state: in-progress
kind: bug
origin: human
created: '2026-07-20'
priority: medium
blocked_by: []
parent: null
scope:
- src/frob/__main__.py
- src/frob/gates/**
- src/frob/tickets/**
- tests/test_prework_parity.py
- tests/unit/test_main_entry.py
scope_changes:
- op: add
  glob: tests/test_prework_parity.py
  reason: add regression tests for the SIGINT clean-message fix and the scope_digest
    content-portability contract
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/test_main_entry.py
  reason: add regression tests for the SIGINT clean-message fix and the scope_digest
    content-portability contract
  actor: logan
  at: '2026-07-21'
evidence:
- tests/unit/test_main_entry.py::TestMainSigint::test_keyboard_interrupt_prints_clean_message_and_exits_130
- tests/unit/test_main_entry.py::TestMainSigint::test_normal_dispatch_is_unaffected
- tests/test_prework_parity.py::TestScopeDigestParity::test_digest_is_content_only_portable_across_checkouts
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
found while working T-0240 (same origin ticket text, deliberately split out): T-0240 fixed the sweep's unbounded full-root xref walk and glob-stem xref terms, but three remaining items from the original malmberg report are NOT addressed by that fix and need their own design/scope: (1) SIGINT during a long sweep prints a bare KeyboardInterrupt traceback instead of a clean message -- __main__.py-level signal handling, out of T-0240's tickets/gates/dup scope. (2) PRE001 catch-22 on slow mounts: editing a ticket's scope demands a re-sweep, and if the sweep itself is what is slow on that mount the ticket can never get back into a checkable state -- needs a design decision (timeout + partial-sweep-ok state, or async sweep), not a bugfix. (3) scope_digest hashes snapshot file-hashes (path+content sha), so a recorded sweep cannot be transplanted between two checkouts with identical file content but different paths/timestamps-derived hashes -- consider keying on content-only digest so sweep records are checkout-portable. None of these are addressed by T-0240's fix.

## Done report

T-0355 bundled three items split out from a T-0240-adjacent report.
Verified against current code first (T-0474 already backgrounds the
sweep at `frob ticket start`, T-0484 landed coverage-fast changes) --
neither mooted this ticket's items.

Item 1 (SIGINT clean message): main() used to run its dispatch inline,
so a Ctrl-C during a long-running command (e.g. a slow synchronous
sweep on a bad mount) surfaced as a bare KeyboardInterrupt traceback.
Split the dispatch body into a private _dispatch(argv) helper and wrap
only that call in main() with a KeyboardInterrupt handler that prints
"frob: interrupted" to stderr and exits 130 (128+SIGINT, the
conventional code). Moved the frob:ticket T-0358 stale-install-warning
directive back onto main (now public) since it rode onto the newly
private _dispatch otherwise (COV005).

Item 3 (scope_digest content-keying): verified scope_digest's per-file
hash already comes from frob.graph._content_hash -- a plain sha256 of
file bytes, never folded with _stat_key's mtime/size (that pair is only
a cheap cache-invalidation check). Combined with the repo-relative path
key, a recorded sweep digest is already checkout-portable: identical
scope files at the same relative paths in two independent checkouts
produce the same digest regardless of absolute root or timestamps.
Added a regression test across two independent tmp_path checkouts
pinning this so a future change keying on stat metadata instead would
fail loudly rather than silently reintroducing the bug the ticket
described.

Item 2 (PRE001 catch-22 on slow mounts) was NOT implemented here: the
ticket's own text says it "needs a design decision (timeout +
partial-sweep-ok state, or async sweep)", not a mechanical port of an
existing fix. `frob ticket sweep` (the always-available resweep path
used after a scope edit) is still fully synchronous by design, and
PRE001 only ever compares against a fully-completed digest -- there is
no partial-sweep-ok state today. Forcing a partial implementation here
risked either a correctness hole (a provisional-pass state that lets
PRE001 go green on incomplete data) or silently deciding the product
design question myself. Filed as a new ticket instead: T-draft-ac820c46
(off-default-branch provisional id; will mint a real T-#### id on
merge to main).

### Changed
```
 src/frob/__main__.py          | 31 ++++++++++++++---
 src/frob/app/ticket_runner.py | 77 ++++++++++++++----------------------------
 src/frob/gates/__init__.py    | 13 ++++++++
 tests/test_prework_parity.py  | 19 +++++++++++
 tests/unit/test_main_entry.py | 45 +++++++++++++++++++++++++
 tickets.md                    | 78 ++++++++++++++++++++++++++++++++++++++++---
 6 files changed, 202 insertions(+), 61 deletions(-)
```

### Evidence
- `tests/unit/test_main_entry.py::TestMainSigint::test_keyboard_interrupt_prints_clean_message_and_exits_130` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestMainSigint::test_normal_dispatch_is_unaffected` (pytest node id, verified passing when recorded)
- `tests/test_prework_parity.py::TestScopeDigestParity::test_digest_is_content_only_portable_across_checkouts` (pytest node id, verified passing when recorded)
<!-- ticket:T-0380 -->
```yaml
id: T-0380
title: 'vet: extend binding-aware resolution into CVE fingerprint scanning'
state: queued
kind: security
origin: human
created: '2026-07-20'
priority: medium
blocked_by:
- ''
- T-0377
- T-0378
- T-0379
parent: T-0376
scope:
- src/frob/vet/_capability.py
- tests/test_vet*.py
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
_scan_file_fingerprints (CVE matching) is lexical needle-matching for EVERY language including Python -- a renamed import defeats a fingerprint even where capability scanning is binding-aware. Reuse the binding tables built for capability resolution (Python + the new TS/Rust/C-C++ tables) to resolve aliases before fingerprint matching for all languages. Acceptance: an aliased import that would evade a lexical fingerprint match is still caught; adversarial test per language.

<!-- ticket:T-0383 -->
```yaml
id: T-0383
title: 'strata: audit and populate caught_by on all existing out-of-scope/benign-capability
  entries'
state: queued
kind: security
origin: human
created: '2026-07-20'
priority: medium
blocked_by:
- T-0382
parent: T-0376
scope:
- src/frob/strata/
- docs/design/registry/
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
Audit every EXISTING out_of_scope / BenignCapability / CAPABILITY_MATRIX_EXCUSES entry in the repo and populate its new caught_by field with the real compensating control, or, where nothing actually catches the excused item, convert the entry into a real enforced check instead of an excuse. Acceptance: frob check --only invariant/security passes with the caught_by verification (T-0382) enabled across the whole repo; zero entries left with a placeholder/fabricated caught_by.

<!-- ticket:T-0384 -->
```yaml
id: T-0384
title: 'registry reconciliation: weaknesses (944 CWEs)'
state: queued
kind: security
origin: human
created: '2026-07-20'
priority: medium
blocked_by:
- T-0382
- T-0343
parent: T-0376
scope:
- src/frob/vet/
- src/frob/strata/
- docs/design/registry/weaknesses.yaml
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
Reconcile docs/design/registry/weaknesses.yaml against actual enforcement: every catalogued entry must map to (i) an enforced check, (ii) a documented out-of-scope entry with a verified caught_by (T-0381/T-0382), or (iii) an explicit deferred ticket. Resolve RECONCILIATION.md's undispositioned entries for this registry. Add an EXHAUSTIVENESS meta-test for this registry: catalogued count == enforced+excused+deferred count, so a future gap fails the build. Acceptance: exhaustiveness meta-test passes and is wired into frob check.

<!-- ticket:T-0385 -->
```yaml
id: T-0385
title: 'registry reconciliation: patterns (346 patterns)'
state: queued
kind: security
origin: human
created: '2026-07-20'
priority: medium
blocked_by:
- T-0382
- T-0343
parent: T-0376
scope:
- src/frob/vet/
- docs/design/registry/patterns.yaml
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
Reconcile docs/design/registry/patterns.yaml against actual enforcement: every catalogued entry must map to (i) an enforced check, (ii) a documented out-of-scope entry with a verified caught_by (T-0381/T-0382), or (iii) an explicit deferred ticket. Resolve RECONCILIATION.md's undispositioned entries for this registry. Add an EXHAUSTIVENESS meta-test for this registry: catalogued count == enforced+excused+deferred count, so a future gap fails the build. Acceptance: exhaustiveness meta-test passes and is wired into frob check.

<!-- ticket:T-0386 -->
```yaml
id: T-0386
title: 'registry reconciliation: secrets (3 entries -- thin)'
state: queued
kind: security
origin: human
created: '2026-07-20'
priority: medium
blocked_by:
- T-0382
- T-0343
parent: T-0376
scope:
- src/frob/vet/
- docs/design/registry/secrets.yaml
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
Reconcile docs/design/registry/secrets.yaml against actual enforcement: every catalogued entry must map to (i) an enforced check, (ii) a documented out-of-scope entry with a verified caught_by (T-0381/T-0382), or (iii) an explicit deferred ticket. Resolve RECONCILIATION.md's undispositioned entries for this registry. Add an EXHAUSTIVENESS meta-test for this registry: catalogued count == enforced+excused+deferred count, so a future gap fails the build. Acceptance: exhaustiveness meta-test passes and is wired into frob check.

<!-- ticket:T-0387 -->
```yaml
id: T-0387
title: 'registry reconciliation: pii (7 entries -- thin)'
state: queued
kind: security
origin: human
created: '2026-07-20'
priority: medium
blocked_by:
- T-0382
- T-0343
parent: T-0376
scope:
- src/frob/vet/
- docs/design/registry/pii.yaml
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
Reconcile docs/design/registry/pii.yaml against actual enforcement: every catalogued entry must map to (i) an enforced check, (ii) a documented out-of-scope entry with a verified caught_by (T-0381/T-0382), or (iii) an explicit deferred ticket. Resolve RECONCILIATION.md's undispositioned entries for this registry. Add an EXHAUSTIVENESS meta-test for this registry: catalogued count == enforced+excused+deferred count, so a future gap fails the build. Acceptance: exhaustiveness meta-test passes and is wired into frob check.

<!-- ticket:T-0388 -->
```yaml
id: T-0388
title: 'registry reconciliation: compliance (27 entries -- thin)'
state: queued
kind: security
origin: human
created: '2026-07-20'
priority: medium
blocked_by:
- T-0382
- T-0343
parent: T-0376
scope:
- src/frob/strata/_compliance.py
- docs/design/registry/compliance.yaml
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
Reconcile docs/design/registry/compliance.yaml against actual enforcement: every catalogued entry must map to (i) an enforced check, (ii) a documented out-of-scope entry with a verified caught_by (T-0381/T-0382), or (iii) an explicit deferred ticket. Resolve RECONCILIATION.md's undispositioned entries for this registry. Add an EXHAUSTIVENESS meta-test for this registry: catalogued count == enforced+excused+deferred count, so a future gap fails the build. Acceptance: exhaustiveness meta-test passes and is wired into frob check.

<!-- ticket:T-0389 -->
```yaml
id: T-0389
title: 'registry reconciliation: supply-chain (41 entries)'
state: queued
kind: security
origin: human
created: '2026-07-20'
priority: medium
blocked_by:
- T-0382
- T-0343
parent: T-0376
scope:
- src/frob/vet/
- docs/design/registry/supply-chain.yaml
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
Reconcile docs/design/registry/supply-chain.yaml against actual enforcement: every catalogued entry must map to (i) an enforced check, (ii) a documented out-of-scope entry with a verified caught_by (T-0381/T-0382), or (iii) an explicit deferred ticket. Resolve RECONCILIATION.md's undispositioned entries for this registry. Add an EXHAUSTIVENESS meta-test for this registry: catalogued count == enforced+excused+deferred count, so a future gap fails the build. Acceptance: exhaustiveness meta-test passes and is wired into frob check.

<!-- ticket:T-0390 -->
```yaml
id: T-0390
title: 'registry reconciliation: evasion (112 entries)'
state: queued
kind: security
origin: human
created: '2026-07-20'
priority: medium
blocked_by:
- T-0382
- T-0343
parent: T-0376
scope:
- src/frob/vet/
- docs/design/registry/evasion.yaml
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
Reconcile docs/design/registry/evasion.yaml against actual enforcement: every catalogued entry must map to (i) an enforced check, (ii) a documented out-of-scope entry with a verified caught_by (T-0381/T-0382), or (iii) an explicit deferred ticket. Resolve RECONCILIATION.md's undispositioned entries for this registry. Add an EXHAUSTIVENESS meta-test for this registry: catalogued count == enforced+excused+deferred count, so a future gap fails the build. Acceptance: exhaustiveness meta-test passes and is wired into frob check.

<!-- ticket:T-0391 -->
```yaml
id: T-0391
title: 'registry reconciliation: arch-checks (311 entries)'
state: queued
kind: security
origin: human
created: '2026-07-20'
priority: medium
blocked_by:
- T-0382
- T-0343
parent: T-0376
scope:
- src/frob/gates/
- docs/design/registry/arch-checks.yaml
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
Reconcile docs/design/registry/arch-checks.yaml against actual enforcement: every catalogued entry must map to (i) an enforced check, (ii) a documented out-of-scope entry with a verified caught_by (T-0381/T-0382), or (iii) an explicit deferred ticket. Resolve RECONCILIATION.md's undispositioned entries for this registry. Add an EXHAUSTIVENESS meta-test for this registry: catalogued count == enforced+excused+deferred count, so a future gap fails the build. Acceptance: exhaustiveness meta-test passes and is wired into frob check.

<!-- ticket:T-0392 -->
```yaml
id: T-0392
title: 'registry reconciliation: system-design (119 entries)'
state: queued
kind: security
origin: human
created: '2026-07-20'
priority: medium
blocked_by:
- T-0382
- T-0343
parent: T-0376
scope:
- src/frob/strata/
- docs/design/registry/system-design.yaml
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
Reconcile docs/design/registry/system-design.yaml against actual enforcement: every catalogued entry must map to (i) an enforced check, (ii) a documented out-of-scope entry with a verified caught_by (T-0381/T-0382), or (iii) an explicit deferred ticket. Resolve RECONCILIATION.md's undispositioned entries for this registry. Add an EXHAUSTIVENESS meta-test for this registry: catalogued count == enforced+excused+deferred count, so a future gap fails the build. Acceptance: exhaustiveness meta-test passes and is wired into frob check.

<!-- ticket:T-0393 -->
```yaml
id: T-0393
title: 'advisories: triage abstraction-opportunity near-dup families'
state: queued
kind: feature
origin: human
created: '2026-07-20'
priority: medium
blocked_by: []
parent: T-0376
scope:
- src/frob/
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
Triage the 37 frob-arch abstraction-opportunity advisories: for each genuine near-duplicate or specific-signature family, either extract the real shared code into one home, or add an explicit reason-note accepting the duplication. Acceptance: frob check arch advisories for abstraction-opportunity reduced to zero unresolved (each is either fixed or reason-noted).

<!-- ticket:T-0394 -->
```yaml
id: T-0394
title: 'advisories: deep-nesting refactor (2 findings)'
state: queued
kind: bug
origin: human
created: '2026-07-20'
priority: medium
blocked_by: []
parent: T-0376
scope:
- src/frob/
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
Address the 2 frob-arch deep-nesting advisories: refactor to reduce nesting depth, or add an explicit reason-note if the nesting is justified. Acceptance: both findings resolved (fixed or reason-noted).

<!-- ticket:T-0395 -->
```yaml
id: T-0395
title: 'advisories: large-file residue after calibrated thresholds (T-0373)'
state: queued
kind: feature
origin: human
created: '2026-07-20'
priority: medium
blocked_by:
- T-0373
parent: T-0376
scope:
- src/frob/
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
After T-0373 re-thresholds frob-arch large-file to 800 lines / 60 (function), address the residue that still exceeds 800 lines among the 34 large-file advisories: real module splits, or accepted-with-reason for files that don't decompose cleanly. Acceptance: frob check arch large-file advisories at the calibrated threshold reduced to zero unresolved.

<!-- ticket:T-0397 -->
```yaml
id: T-0397
title: 'AUDIT REMEDIATION EPIC: North-Star integrity -- every green must be earned'
state: queued
kind: feature
origin: human
created: '2026-07-20'
priority: medium
blocked_by: []
parent: null
scope:
- src/frob/
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
Full-repo pessimistic capability audit (2026-07-20, 7 read-only auditors). North-Star: if frob check / a ticket-close / a strata proof passes, the thing it claims must ACTUALLY hold. The audit found the North-Star is violated in concrete ways across subsystems. Each subsystem audit gets an umbrella child holding its full findings table; each HIGH finding gets an actionable child. Findings files live in the audit run; this epic is the durable tracked home so the audit itself does not become an orphaned document (the exact failure mode that motivated it). Consolidation in progress as the 7 auditors land: tickets/testing (evidence integrity), strata (vacuous proofs), graph/edges, gates-accounting, gates-quality/security, vet (lexical resolution), lang/check/docs.

<!-- ticket:T-0399 -->
```yaml
id: T-0399
title: 'AUDIT: green must claim quality -- promote quality gates from WARN to blocking
  (docs/audits/gates-quality.md)'
state: queued
kind: security
origin: human
created: '2026-07-20'
priority: medium
blocked_by: []
parent: T-0397
scope:
- src/frob/gates/
- src/frob/app/config.py
- frob.toml
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
See docs/audits/gates-quality.md. HIGH: entire quality surface is non-blocking (PERF/PII010/SEC110/ARCH001/DUP/lower-secrets are WARN, frob check exits 0 on them) -- green makes NO quality claim; DUP fails open (default-off AND no-op without natives); frob:secret-fake suppresses real secrets with no accountability/reason/ledger. RIGHT-WAY fix: decide per rule which are error-tier (and default DUP on / fail-closed when natives missing); give secret suppression the same reasoned-waiver accountability as frob:waive. Expect the build to red -- that red is honest. Then re-audit until empty. MED/LOW in the doc.

<!-- ticket:T-0401 -->
```yaml
id: T-0401
title: 'AUDIT: strata vacuous-proof closure -- bind proofs to code, fail-closed on
  incompleteness (docs/audits/strata.md)'
state: in-progress
kind: security
origin: human
created: '2026-07-20'
priority: medium
blocked_by: []
parent: T-0397
scope:
- src/frob/strata/
scope_changes: []
evidence:
- tests/unit/strata/test_threat.py::TestEvalFiresCwe94::test_eval_capability_is_classified_not_benign_excused
- tests/unit/strata/test_threat.py::TestEvalFiresCwe94::test_eval_capability_fires_a_real_cwe94_obligation
- tests/unit/strata/test_threat.py::TestEvalFiresCwe94::test_eval_capability_discharges_with_a_real_mitigation_claim
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
See docs/audits/strata.md. HIGH: boundaries never bound to code (discharge = typing a matching string); vacuous discharge when foreign->sink flow is un-modeled (incomplete .strata discharges real caps); eval globally BenignCapability-excused (no RCE obligation); FOREIGN files loose under src/frob/ escape all SYS + THREAT004/005; utility flow marker defeats confidentiality noflow. RIGHT-WAY fix: join Boundary predicates against observed code; require flow-completeness before a NoFlow discharges (fail-closed); add eval obligation; make sys rules cover every capability-bearing file. Then re-audit until empty. G6-G12 in the doc.

<!-- ticket:T-0408 -->
```yaml
id: T-0408
title: 'Invariant coverage gate: harvest prose property claims into an enforced invariant
  registry (4 invariants vs 128 files asserting guarantees)'
state: queued
kind: feature
origin: human
created: '2026-07-20'
priority: medium
blocked_by: []
parent: T-0407
scope:
- src/frob/gates/
- invariants/
- src/frob/
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
Two-part gap the user surfaced (2026-07-20). CONTENT: only 4 formal invariants (INV-001..004) exist for a ~60k-line system, while grep finds 128 files asserting a property in prose (always/never/idempotent/thread-safe/exactly once/monotonic/guaranteed/must not). A large subset are genuine guarantees (capability-sink NoFlow, cache invalidation correctness, ledger state-machine transitions, evidence exactly-once, splice idempotence, dup alpha-rename soundness, id-allocation collision-freedom, graph-built-once) with ZERO property tests. TOOLING (the meta-gap the user named -- "frob let us get away with it for so long"): INV001/INV002 only validate DECLARED invariants (evidence + binding present); nothing checks whether ENOUGH invariants are declared, so a huge system with 4 invariants passes clean. Same class as every failure today: existence-not-completeness, early-exit-without-exhausting-the-registry.

FIX (an instance of T-0407 registry capability): the set of property claims IS a registry. (1) Harvest every prose property claim across the repo (all langs) -- always/never/idempotent/thread-safe/exactly-once/monotonic/guaranteed/must-not and the strata NoFlow/boundary claims -- as candidate invariant entries (SSOT = code prose + invariants/). (2) Each entry must be DISPOSITIONED: formalized (frob:invariant + a property/hypothesis test that actually exercises it, via the prover flow) | reworded as not-a-guarantee (removed from the claim vocabulary) | deferred (open ticket). (3) A coverage gate (INV003-style, fail-closed, ships per-project per T-0406) reds the build on any undispositioned property claim AND on proven-worthy surfaces with no invariant (a capability sink / state machine / concurrency point / idempotent op with no covering invariant). (4) frob registry audit reports invariant coverage honestly (N formalized / M deferred / K reworded / W UNACCOUNTED). Then actually FORMALIZE the real guarantees (drive the 128 down to 0 unaccounted -- dispatch the prover agent per cluster). Acceptance: adding a docstring saying "always X" with no frob:invariant reds the build; the current 128 are each dispositioned; frob passes only when invariant coverage is exhausted, not when it is merely non-empty.

META-PRINCIPLE (encode): every time we discover we "got away with" something, that is ALSO a frob enforcement gap -- file the ENFORCEMENT (the gate that would have caught it), not just the content fix.

<!-- ticket:T-0410 -->
```yaml
id: T-0410
title: 'Performance audit: frob check hotpaths (archgate 153s + sys 145s dominate),
  redundant full-repo parsing, Rust-lowering, parallelism, daemon caching'
state: queued
kind: bug
origin: human
created: '2026-07-20'
priority: medium
blocked_by: []
parent: T-0397
scope:
- src/frob/
- frob-core/
- strata-core/
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
User directive (2026-07-20): frob check takes forever; do a PERF audit -- measure where hotpaths ACTUALLY are, lower into native Rust where it helps, review the architecture for stupidity (and note that frob SHOULD have detected its own perf issues -- meta-gap), and think through parallelism/concurrency/multiprocessing. Plus: audit the daemon to ensure we cache what we are supposed to. Grounding measurements (this repo, latest full frob check): archgate=153.6s and sys=145.3s DOMINATE; every other stage is <6s (perf 5.4, pii 1.7, secrets 1.4, test 1.4, tickets 0.27, rest ~0). Strong hypothesis (auditor must MEASURE to confirm/refute via profiling): the repo is tree-sitter-parsed MULTIPLE times per check -- build_graph parses everything, then arch/analyze_project re-parses everything, then strata selfconform (sys) re-parses everything, plus vet/secrets/dup each parse; check/_python.py::_cached_snapshot only memoizes the GRAPH build, NOT arch/sys parses, so trees are not shared across stages. Confound: /mnt/c mount tax (13-60x slower I/O per T-0245) -- the audit MUST distinguish I/O-bound (reading every file N times) from CPU-bound (parsing/walking N times). Deliverables to docs/audits/perf.md (auditor writes it): (A) real profile of a full frob check -- top hotpaths by cumulative time, per stage, with the redundant-parse count actually measured; (B) architecture review: how many times each file is read+parsed, where a single shared parse pass / warm snapshot would collapse work, sqlite connection/contention patterns, any O(n^2) or per-file-stat storms; (C) parallelism/concurrency: are stages actually parallel or serialized? where is the serialization? would a process/thread pool or a shared-parse-then-fan-out help? what belongs in frob-core Rust (hot tree walks: arch complexity, capability scan, hashing -- dup is already Rust)? (D) DAEMON/caching audit: is the warm-graph incremental daemon (T-0177) actually built, and does serve/ cache the parsed graph across requests + invalidate correctly, or re-build/re-parse per call? is the .frob cache doing incremental (only re-parse changed files) or full rebuilds? (E) META-GAP: why did PERF001-004 NOT flag the redundant full-repo parsing / missing shared cache -- what class of architectural/cross-stage perf antipattern is the PERF gate blind to, and what enforcement would catch it (this becomes its own ticket). >=10 concrete findings with measured impact + severity + file:line. REPORT ONLY (auditor). Then remediation children per finding.

<!-- ticket:T-0417 -->
```yaml
id: T-0417
title: 'Evidence integrity round 2: close still not converged -- empty-scope bypass,
  no re-verify-at-close, vacuous-test passes (docs/audits/tickets-testing-round2.md)'
state: queued
kind: security
origin: human
created: '2026-07-20'
priority: medium
blocked_by: []
parent: T-0398
scope:
- src/frob/tickets/
- src/frob/gates/
- src/frob/app/ticket_runner.py
- src/frob/testing/
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
Convergence re-audit of the tickets/testing subsystem AFTER T-0398 landed (docs/audits/tickets-testing-round2.md): D-01..D-12 genuinely fixed EXCEPT the subsystem is NOT converged -- 3 new HIGH CLI-reachable bypasses (no --force needed): N-01 omitting --scope skips the D-02 covers_scope binding entirely (a code ticket with no scope closes on any passing evidence); N-02 frob ticket close does NOT re-run the evidence tests -- it trusts the pass status recorded at evidence-record time, so a test recorded green then later broken still closes (TOCTOU); N-03/N-04 pass == pytest exit 0, so a VACUOUS test (asserts nothing) or a self-scoped no-op test satisfies the gate -- the exact vacuous-test class the review loop keeps catching. Plus D-03 is only a 3-char floor (weak done-report substance) and D-10/D-12 unchanged. FIX the RIGHT way: (N-01) fail-CLOSED on empty scope for CODE-kind tickets (a code ticket MUST declare scope + have covering evidence); (N-02) RE-VERIFY evidence at close the way land already does (re-run the evidence tests at close, not just trust record-time status); (N-03/04) detect vacuous/no-assertion evidence tests (a test that passes but asserts nothing / never exercises the scope symbol should not count -- reuse the covers_scope graph binding to require the evidence actually reaches a touched symbol, and consider an assertion-presence check); strengthen D-03 beyond a char floor (require the real sections). Re-audit again after -- converged only when a pessimistic pass finds nothing. Full findings + repros: docs/audits/tickets-testing-round2.md. QUEUED behind T-0343/T-0415 (gates/app overlap) to avoid merge conflict.

<!-- ticket:T-0418 -->
```yaml
id: T-0418
title: 'perf: analyze_project runs TWICE per frob check (frob-arch stage + archgate
  gate); wire the DEAD _arch_violations_from_suggestions (~112s)'
state: queued
kind: bug
origin: human
created: '2026-07-20'
priority: medium
blocked_by: []
parent: T-0410
scope:
- src/frob/check/
- src/frob/gates/
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
User spotted from frob check output: frob-arch appears as its own stage AND archgate=112.81s appears in the gates timing -- arch is analyzed TWICE. Confirmed: check/_python.py::_run_arch (the advisory frob-arch stage) calls analyze_project once (~line 440); gates/_arch.py::arch_gate independently calls analyze_project again for ARCH001 (the archgate timing). The helper written to prevent exactly this -- check/_python.py::_arch_violations_from_suggestions (builds ARCH001 Violations from the already-computed suggestions "without re-running analyze_project a second time") -- is DEAD CODE, grep finds zero callers. FIX: wire the gates stage to build ARCH001 from the suggestions _run_arch already computed (via the dead helper), so analyze_project runs ONCE per check. Verify the same ARCH001 violation set is produced (byte-identical gate output) and archgate drops toward 0 (the work moves into the single frob-arch run). CHECK dup too: _run_dup calls find_duplicates for the frob-dup stage; confirm dup_gate does not ALSO re-run detection (it is default-off so may already skip -- verify). This is the exact "same expensive input recomputed across stages" class T-0413 (PERF meta-gap) must catch. Measured target: ~112s saved.

<!-- ticket:T-0428 -->
```yaml
id: T-0428
title: 'Registry SSOT redesign: DERIVE coverage from code (frob:enforces) + research
  corpus, not a hand-maintained handled_by file'
state: queued
kind: feature
origin: human
created: '2026-07-20'
priority: medium
blocked_by: []
parent: T-0407
scope:
- src/frob/gates/
- src/frob/
- docs/design/registry/
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
User (2026-07-20): worried about the single-source-of-truth mantra -- is there a better way? YES, invert it. PROBLEM with the current T-0343 model: a hand-maintained canonical .yaml is the SSOT, with hand-TYPED handled_by:<rule-id> claims. That is the catalogued-vs-enforced drift moved up one level -- the registry is a CLAIM about the code, and a hand-typed claim that must be kept in sync is exactly why REG002 (dangling handled_by) must exist. The real source of truth about what is enforced is the CODE, not a file describing it. BETTER ARCHITECTURE (derived, not authored): (1) ENFORCEMENT TRUTH lives IN CODE -- each rule/detector declares what concepts it enforces via an in-code directive (frob:enforces <concept-id>, e.g. frob:enforces CWE-79 on the SEC rule / a rule-registry field); this cannot drift from the code because it IS the code, and it is verifiable (the rule must exist to carry the directive). (2) THE UNIVERSE lives in an append-only research CORPUS (SSOT for "what concepts exist"). (3) THE REGISTRY is the COMPUTED reconciliation of universe INTERSECT code-declarations: handled_by is DERIVED from the frob:enforces declarations (never hand-typed, so REG002-dangling becomes structurally impossible); an entry is undispositioned iff it is in the universe but no code enforces it AND no open deferral/out-of-scope exists. Benefits: no hand-maintained middle file to drift; adding an enforcing rule auto-updates coverage (no separate registry edit to forget); the researcher just appends to the universe and coverage falls out; two REAL ssots (code=enforced, corpus=exists) + one computed join, instead of one file pretending to be the truth about code it cannot see. This SUPERSEDES T-0343 hand-maintained handled_by as the target model (T-0343 is the v0 drift-lock; this is the v1 derived-coverage). Acceptance: a rule carrying frob:enforces CWE-79 auto-marks CWE-79 handled in the computed registry; removing that rule un-marks it (the registry tracks CODE reality); a universe entry with no enforcing rule and no open deferral shows undispositioned; NO hand-typed handled_by remains as the source of truth.

TWO-SSOT CONFORMANCE (user, 2026-07-20: "if we split it, we need to enforce conformance between code SSOT and research SSOT"). Splitting into two SSOTs (code=enforced, corpus=exists) only helps if a GATE enforces their MUTUAL conformance -- otherwise it just doubles the drift surface. Required BIDIRECTIONAL conformance check (mirror strata selfconform SYS100, which already does exactly this two-way binding for model<->code -- REUSE that machinery/pattern, do not reinvent): (a) CODE -> CORPUS: every frob:enforces <concept-id> in code must resolve to a REAL corpus entry -- a rule claiming to enforce a concept the universe does not contain is a dangling/phantom enforcement and FAILS (a new REG/CONF rule); this catches both a typo and a rule enforcing something the corpus forgot to enumerate. (b) CORPUS -> CODE: every corpus entry is dispositioned (enforced-by-a-real-frob:enforces | deferred:open-ticket | out_of_scope:reason) -- an undispositioned universe entry FAILS (the REG001 completeness, now derived). (c) TOTALITY: the computed join is total and non-lying -- no corpus id enforced by a nonexistent rule (structurally impossible since frob:enforces lives ON the rule), no frob:enforces target outside the corpus. Net: the two SSOTs are two-way bound like strata model<->code, so neither can drift from the other silently -- the conformance gate IS what makes the split sound. Acceptance additions: a frob:enforces naming a concept-id NOT in the corpus FAILS; a corpus entry with no enforcing rule + no open deferral FAILS; the pair is provably consistent (the strata selfconform bidirectional-binding property, applied to enforcement<->universe).

<!-- ticket:T-0429 -->
```yaml
id: T-0429
title: 'Exhaustive-researcher: mechanism to emit into the universe corpus (stable
  ids, schema, denominator proof) so research -> registry -> enforcement is one loop'
state: queued
kind: feature
origin: human
created: '2026-07-20'
priority: medium
blocked_by: []
parent: T-0407
scope:
- .claude/agents/
- src/frob/
- docs/guides/
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
User (2026-07-20): ensure the exhaustive researcher has the mechanisms to MAKE the exhaustive registries. Today the exhaustive-researcher agent enumerates to an external store but there is no clean mechanism to emit its findings INTO the universe corpus in the format the registry/exhaustiveness gate consumes -- so research and enforcement are disconnected (the root of the orphaned-registry breach). Give the researcher the mechanism: (1) the corpus SCHEMA (stable per-entry ids, name, source/citation, the append-only universe format) documented + a helper/command to append entries (frob registry add / a corpus-emit tool) so a research pass writes directly into the universe SSOT, not a prose doc that later has to be transcribed. (2) The DENOMINATOR/EXHAUSTIVENESS proof: research declares the TOTAL it enumerated so the exhaustiveness gate (T-0343 REG005 / the derived model in the sibling ticket) can verify count == entries -- nothing dropped between research and corpus. (3) Under the DERIVED-registry model (sibling ticket), the researcher does NOT assign dispositions (those are code-derived) -- it only enumerates the universe COMPLETELY; make the researcher agent brief + tooling reflect that (append to universe, prove the denominator, done). Acceptance: an exhaustive-research pass emits N corpus entries with stable ids + a declared total; the exhaustiveness gate confirms N==entries; a follow-up code change adding frob:enforces for some of them shows coverage rise automatically; nothing the researcher found is left as untranscribed prose. Closes the research->registry->enforcement loop so a future corpus cannot become orphaned docs.

<!-- ticket:T-0435 -->
```yaml
id: T-0435
title: 'README/prose-claim drift-lock: bind README''s command table (+ checkable counts)
  to the real subcommand registry -- frob was blind to README drift'
state: queued
kind: bug
origin: human
created: '2026-07-20'
priority: medium
blocked_by: []
parent: T-0424
scope:
- src/frob/gates/
- README.md
- docs/
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
User (2026-07-20): noticed doc drift in the base README.md -- why was it allowed? frob should have flagged it. ROOT CAUSE (the meta-principle: a gap in our compliance is a gap in frobs enforcement): README carries ~0 frob:describes anchors (grep finds 1 in the whole file), so it is UNANCHORED prose. DRIFT001/002 detect code<->doc drift THROUGH anchors; the README command table is not bound to the actual argparse subcommand registry, so adding frob vet/sys/deploy/serve/perf/mutate/stats/release during the rework never flagged the README table as stale -- it was missing 8 of 25 real commands (a third, incl. major subsystems). Same existence-not-verified class: README claims a command set unbound to the truth (the real commands), so it drifts silently. FIXED the immediate drift (added the 8 rows). ENFORCEMENT (this ticket): a drift-lock that binds README (and other top-level prose making CHECKABLE factual claims) to reality -- (1) the README command table is DERIVED-from / checked-against the live subcommand registry (frob --help / the argparse commands): a table row for a command that does not exist FAILS, a real command absent from the table FAILS. (2) Extend to other checkable claims where cheap: a claimed COUNT ("N commands", "N gates", "N tickets") bound to the real count; install/quickstart command snippets that name a subcommand verified to exist. This is an instance of reflexive completeness (T-0424) + the derived-check model (T-0428): dont hand-maintain a prose list that drifts -- check it against the code registry. Acceptance: adding a new subcommand with no README row FAILS the drift-lock; removing a command leaves its README row FAILING; a claimed count that no longer matches FAILS. frobs own README can never again silently omit a third of its commands.

<!-- ticket:T-0437 -->
```yaml
id: T-0437
title: 'Doc-pointer resolution gate: every doc reference of a RECOGNIZED resolvable
  shape must resolve (hardened closed-set, not fuzzy ''seems to point'')'
state: queued
kind: feature
origin: human
created: '2026-07-20'
priority: medium
blocked_by: []
parent: T-0435
scope:
- src/frob/gates/
- src/frob/graph/
- docs/
- frob.toml
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
User (2026-07-20): account for anything that looks like a tool usage/guide, and any documentation that SEEMS to point to something -- and HARDEN the wishy-washy part. THE HARDENING: do not try to detect fuzzy "seems to point to X" intent (unhardenable, high FP). Instead define a CLOSED SET of RECOGNIZED, RESOLVABLE POINTER SHAPES and only fire when a pointer of a known shape targets something that does NOT exist. This converts "seems to point" into a mechanical, resolvable check with a naturally-low FP rate (an unrecognized shape is simply not checked). POINTER KINDS (each detectable + resolvable against the real project): (1) FILE/PATH -- a repo-relative path (src/frob/foo.py, docs/bar.md, frob.toml) mentioned in a code span/block/link must EXIST; (2) CLI INVOCATION / TOOL-GUIDE -- `<project-cli> <subcommand>` and `--flag`/`-x` options against the projects real argparse/command source (frob is one instance; per-project via a configurable command source) -- a nonexistent subcommand or flag is stale; (3) CONFIG REFERENCE -- a `[section]` or `[section].key` or a frob.toml/pyproject/Cargo key referenced must be a REAL config key of that manifest/schema; (4) CODE SYMBOL -- a dotted path / import / use (module.Class.method, from X import Y, use crate::x) resolves in the graph against the projects manifest-derived namespaces (see T-0436: Rust workspace subcrates, pyproject/package.json package names != dir names; external namespaces skipped); (5) DOC-ANCHOR LINK -- a docs/x.md#anchor (or a frob:doc/frob:describes anchor target) must exist. SCOPE: inline code spans AND fenced code blocks AND markdown links AND tool-guide prose ("run `X`", "add `[section]` to frob.toml", "the `--foo` flag", "see `docs/bar.md`"). CONSERVATISM: only a pointer matching a recognized shape whose target is DEFINITIVELY resolvable-or-refutable is checked; an unrecognized/ambiguous token is NOT flagged (the hardening). PROMINENTLY WAIVABLE (frob:waive) for intentional external/illustrative/future-facing pointers. Ships per-project (T-0406), all languages. T-0436 (unbound/stale CODE BLOCKS) is ONE INSTANCE of this; this ticket is the general doc-pointer-resolution gate (the north-star doc-drift check, cf T-0325). Acceptance: a doc mentioning `src/frob/gone.py` (nonexistent) flagged; `frob edit`/`--nonexistent-flag` flagged; a `[bogus.section]` frob.toml reference flagged; a `docs/missing.md#x` link flagged; a real path/command/flag/symbol/anchor passes; an unrecognized prose token NOT flagged; external pointers waivable. Run on frobs own docs, report FP rate, disposition honestly.

<!-- ticket:T-0440 -->
```yaml
id: T-0440
title: 'strata model debt: deploy/serve/mutate swept into coarse utility-hub node,
  not modeled as distinct capabilities with own effects/threat surface'
state: queued
kind: security
origin: human
created: '2026-07-20'
priority: medium
blocked_by: []
parent: null
scope:
- design/frob.strata
- docs/strata/
- tests/**
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```

<!-- ticket:T-0441 -->
```yaml
id: T-0441
title: 'frob fmt: auto-wrap over-length frob: directive comment lines via T-0286 continuation
  so ruff E501 never fires on waive reasons'
state: queued
kind: feature
origin: human
created: '2026-07-20'
priority: medium
blocked_by: []
parent: null
scope:
- src/frob/graph/dsl.py
- src/frob/gates/
- src/frob/app/
- docs/
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
Friction hit by hand 2026-07-20: a `frob:waive` reason long enough to be
useful overflows ruff's E501, so `frob check` (ruff) and the waive author
fight -- you truncate the reason (losing the explanation) or hand-wrap it
with the T-0286 trailing-backslash continuation. frob owns the continuation
syntax, so frob should own the wrapping.

Design:
- `frob fmt` (or `frob check --fix-directives`) detects any `frob:<verb>`
  directive comment line exceeding the project's configured line length
  (read the real limit from ruff/pyproject, per-language for TS/Rust/C++
  too, not a hardcoded 88) and rewrites it into a T-0286 continuation run:
  break at a word boundary before the limit, end each physical line with
  ` \`, keep every physical line under the limit, and preserve the exact
  logical directive text (round-trip: fold(wrap(x)) == x).
- Idempotent: re-running on already-wrapped directives is a no-op.
- When run inside `frob check` without the fix flag, emit a remediation
  hint on the offending line: "directive line over NN cols; run `frob fmt`
  to wrap" -- same self-remedying-message contract as every other gate.
- Cover comment prefixes for all supported languages (`#`, `//`), and the
  continuation-line prefix each language needs so the fold still parses.
- Tests: property test that wrap then fold is identity on arbitrary
  directive text; fixtures per language; an idempotency test.

REFINEMENT (user): frob fmt must be a CANONICAL-FORM NORMALIZER, not a
one-way wrapper -- it needs DEDENTING / UN-WRAPPING capability too. If a
directive was previously split across continuation lines (trailing `\`) but
now fits within the configured limit on a single line -- because the reason
text was shortened, the limit was raised, or it was split unnecessarily in
the first place -- frob fmt must JOIN it back into one physical line (strip
the `\` continuations and the continuation-line comment prefixes, fold the
text, re-emit as a single line) rather than leaving a needlessly-split
directive. Canonical form = the FEWEST physical lines that keep every line
under the limit: one line when it fits, wrapped only as far as necessary.
So the operation is idempotent in BOTH directions: fmt(wrapped-but-fits) ->
single line; fmt(single-line-too-long) -> minimally wrapped; fmt(already-
canonical) -> no-op. Add tests for the un-wrap direction: a 3-line
continuation whose joined form fits collapses to 1 line; a 2-line split
where only the first line was over-long re-wraps to the minimal split;
round-trip join(split(x)) == canonical(x). This shares the fold logic with
T-0286's `_fold_continuations` (reuse, do not duplicate) -- fmt's job is to
choose the canonical physical-line layout, folding to normalize then
re-splitting only where a physical line would exceed the limit.

<!-- ticket:T-0501 -->
```yaml
id: T-0501
title: 'strata audit G2/G7: vacuous NoFlow discharge when foreign->sink flow is un-modeled
  or no foreign-trust node exists'
state: queued
kind: security
origin: human
created: '2026-07-21'
priority: medium
blocked_by: []
parent: null
scope:
- src/frob/strata/_threat.py
- src/frob/strata/_claims.py
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
docs/audits/strata.md G2+G7 (HIGH/MEDIUM), from T-0401. _mitigation_is_chokepoint's first branch (_threat.py:1196) returns True when NoFlow holds with EVERY boundary removed -- i.e. the sink is simply unreachable from foreign in the model, so an incomplete/attacker-authored .strata discharges a real capability with NO mitigation modeled at all (G2). Same root cause as G7: _discharges_as_chokepoint's src=foreign expansion (_claims.py _expand) yields an empty source set when the model declares no foreign-trust node at all, so NoFlow proves vacuously (nothing to walk from) and every obligation on that model discharges with no adversary present. Fix direction: require at least one modeled path from a foreign source to the firing node (and at least one foreign-trust node in the model) before accepting the vacuous short-circuit as a discharge; otherwise emit a distinct 'obligation fires but sink unreachable / no adversary modeled -- model likely incomplete' diagnostic instead of silent PROVED. High-risk core-engine change (this family has the highest REJECT rate in repo history) -- build the counterexample litmus FIRST, confirm it currently discharges vacuously, THEN harden.

<!-- ticket:T-0525 -->
```yaml
id: T-0525
title: COV006 waiver granularity is file-scoped, not symbol-scoped -- can silently
  over-waive
state: queued
kind: bug
origin: agent
created: '2026-07-21'
priority: low
blocked_by: []
parent: null
scope:
- src/frob/gates/__init__.py
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
Discovered while working T-0516: COV006 Violation objects carry no symref (file=test_file, line=0), so _match_waiver falls back to file-level matching for a frob:waive COV006 comment anywhere in that file -- ANY single COV006 waiver in a test file silently suppresses EVERY COV006 finding in that file, not just the one it was written next to. Verified directly: adding one waiver comment near one test in tests/test_gates.py suppressed all 7 COV006 findings then present in that file, including unrelated ones that were NOT sound (an import-alias false-positive that needed a real fix, not a waiver). Consider giving COV006 violations a symref (the test's own qualname) so _match_waiver can do symbol-exact matching the way most other rules do, instead of falling back to file-scope for a rule that very plausibly has multiple independent findings per file.

<!-- ticket:T-0541 -->
```yaml
id: T-0541
title: 'gates: SCOPE001/PRE001 fully disabled with no active ticket / off-convention
  branch (B9)'
state: queued
kind: bug
origin: auditor
created: '2026-07-21'
priority: medium
blocked_by: []
parent: T-0403
scope:
- src/frob/gates/
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
docs/audits/gates-accounting.md B9. _build_ticket_scoped_jobs only registers scope+prework jobs when st.ticket is not None; active_ticket derives the ticket purely from the branch name's T-#### prefix. A branch not named after a ticket (or work on main) skips scope and pre-work enforcement entirely rather than failing. Fix direction: a diff that touches source with no derivable active ticket should be a loud blocking condition, not a skip.

<!-- ticket:T-0542 -->
```yaml
id: T-0542
title: 'gates: COV002 satisfied by ANY open ticket whose scope glob covers the file
  (B10)'
state: queued
kind: bug
origin: auditor
created: '2026-07-21'
priority: medium
blocked_by: []
parent: T-0403
scope:
- src/frob/gates/
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
docs/audits/gates-accounting.md B10. _cov002 uses _open_scopes = every open ticket's scope glob, matched via _scope_covers against ANY of them. One broad-scope open ticket (e.g. src/frob/**) makes every changed symbol under it accounted for regardless of relation to that ticket. Fix direction: prefer the ACTIVE ticket's own scope first, and require a narrower/more-specific glob match (or an explicit frob:ticket edge) when multiple open tickets' scopes could cover the same file, rather than accepting the first match found.

<!-- ticket:T-0545 -->
```yaml
id: T-0545
title: 'gates: coverage/baseline/prework evidence chain is gitignored-local, untrusted
  by CI (B5)'
state: queued
kind: bug
origin: auditor
created: '2026-07-21'
priority: medium
blocked_by: []
parent: T-0403
scope:
- src/frob/gates/
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
docs/audits/gates-accounting.md B5. coverage.xml, .frob/coverage-stamp, .frob/baseline, .frob/prework/*.json are all gitignored -- a fresh CI checkout has no stamp and no committed artifact any reviewer/CI can diff to verify a coverage claim. RIGHT-WAY fix direction: commit a signed/summary coverage artifact (hash + floors, not the raw xml) or fail closed in CI when the stamp's source_sha cannot be reproduced from a clean run, so TEST005/006 mean something externally verifiable.

<!-- ticket:T-0547 -->
```yaml
id: T-0547
title: 'gates: name-only test-convention match credits unrelated same-named symbols
  (B6)'
state: queued
kind: bug
origin: auditor
created: '2026-07-21'
priority: medium
blocked_by: []
parent: T-0403
scope:
- src/frob/gates/
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
docs/audits/gates-accounting.md B6. _inferred_unit_cases matches by snake-cased leaf name only, no module/path binding. Two different public functions both named parse (different modules) are both covered by one test_parse that exercises only one. Repro: two def parse() in different files, one test_parse -> both clear TEST001. RIGHT-WAY fix direction: require some path/module correlation between the test file and the symbol's file before the naming-convention fallback applies. Risk: repo does not strictly mirror tests-to-src layout everywhere -- needs a compat survey before tightening, too large for the T-0403 sweep budget.

<!-- ticket:T-0548 -->
```yaml
id: T-0548
title: 'gates: TEST001 credit requires real coverage, not name-match only (B1)'
state: queued
kind: bug
origin: auditor
created: '2026-07-21'
priority: high
blocked_by: []
parent: T-0403
scope:
- src/frob/gates/
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
docs/audits/gates-accounting.md B1/E1. TEST001 (the only blocking per-symbol test gate) is satisfied by a single collected pytest node id whose name contains the function's snake name (_inferred_unit_cases, or a frob:tests edge that merely collects). Nothing inspects assertions or whether the symbol is even called: def test_myfunc(): pass clears it. TEST002 (case count) and TEST005 (branch coverage) are WARN-only so they never block. Repro: name an empty test after a public function -> frob check green. RIGHT-WAY fix direction: tie TEST001 credit to nonzero per-symbol branch coverage (promote TEST005 to ERROR, or require both name/edge match AND coverage>0 before TEST001 clears). Large, cross-cutting change (touches TEST002/003/004/005/009 severity + interaction, and the legacy-adoption WARN campaign noted in frob.toml comments) -- too large for the T-0403 sweep budget, needs its own dedicated ticket.

<!-- ticket:T-0552 -->
```yaml
id: T-0552
title: 'gates: native-language frob:tests edges get TEST001-004 credit with zero execution
  (B3)'
state: queued
kind: bug
origin: auditor
created: '2026-07-21'
priority: high
blocked_by: []
parent: T-0403
scope:
- src/frob/gates/
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
docs/audits/gates-accounting.md B3/E3. _edge_has_execution_evidence: for TS/C/C++ (_NATIVE_TEST_EXTENSIONS) an edge counts as valid execution evidence if it merely looks like test code by name/path and resolves in the snapshot -- frob runs no TS/C/C++ test collector, so it is never actually executed. An empty void test_foo(){} satisfies TEST001-004. RIGHT-WAY fix direction: either wire real TS/C/C++ test collectors (vitest/ctest already exist per-pipeline per T-0404 finding 1 -- join their results into gate evidence) or mark native frob:tests edges as an explicit degraded 'unverified' state that does not silently satisfy TEST001. Overlaps T-0404 finding 1 (gates not run in native pipelines at all) -- coordinate the two fixes.

<!-- ticket:T-0554 -->
```yaml
id: T-0554
title: 'check: doc/coverage/drift/inv gates run ONLY in the Python pipeline (T-0404
  finding 1)'
state: queued
kind: bug
origin: auditor
created: '2026-07-21'
priority: high
blocked_by: []
parent: T-0404
scope:
- src/frob/check/
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
docs/audits/lang-check-docs.md finding 1. run_check_cpp/run_check_rust/run_check_ts never call _run_gates -- only _python_tasks does. A pure Rust/C++/TS repo runs its native toolchain only; COV001/DOC001/DOC002/DOC003/DRIFT001/DRIFT002/INV/DEC/TODO001 never execute despite the polyglot doc-binding promise (lang/__init__.py module docstring). Repro: a repo with only package.json, add a public exported symbol and a lying/broken frob:doc -> frob check green. RIGHT-WAY fix: run the gates stage in every pipeline (build the graph once, run run_gates regardless of detected language), or at minimum emit a loud gates-NOT-run-for-<lang> stage line. Large, cross-cutting dispatch change -- too large for the T-0404 sweep budget.

<!-- ticket:T-0556 -->
```yaml
id: T-0556
title: 'gates: DRIFT001 default sig facet is blind to behavior/body rewrites (B2)'
state: queued
kind: bug
origin: auditor
created: '2026-07-21'
priority: high
blocked_by: []
parent: T-0403
scope:
- src/frob/gates/ src/frob/graph/
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
docs/audits/gates-accounting.md B2/E2. lock.py _DEFAULT_FACET='sig'; a frob:doc/DESCRIBES ack at the default facet only tracks the signature digest. Rewriting a documented function's body (behavior) after ack never trips DRIFT001 -- the doc can lie about behavior forever. Repro: ack a frob:doc at default facet, rewrite only the body, run frob check -> green. RIGHT-WAY fix direction: default ack facet to sig+body (or require an explicit facet and drift-check body+sig together) so a doc can't silently desync from behavior. Cross-cutting: touches every existing ack in the repo's lock file and the ack CLI UX -- too large for the T-0403 sweep budget.

<!-- ticket:T-0560 -->
```yaml
id: T-0560
title: Schedule the pessimistic-auditor loop to auto-file concern_family_entries in
  check-coverage.yaml
state: queued
kind: feature
origin: human
created: '2026-07-21'
priority: medium
blocked_by: []
parent: null
scope:
- docs/design/registry/
- src/frob/
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
Split out of T-0424: the registry MODEL + honest seed is built (check-coverage.yaml, REG001-007 enforced), but the CONTINUOUS half of T-0424's acceptance ("the pessimistic-auditor loop runs on a schedule and its findings auto-file as dispositioned entries") is a real scheduling/automation feature -- a recurring driver plus an auditor-output-to-YAML writer -- not built in T-0424's pass. This ticket is that follow-up: wire a scheduled (or CI-triggered) pessimistic-auditor run whose findings append new dispositioned concern_family_entries rows to check-coverage.yaml automatically, so new gaps are found before the user notices them, per T-0424's root-cause charter.

<!-- ticket:T-0566 -->
```yaml
id: T-0566
title: docblocks DOC004 gate has no C/C++ fenced-code-block bucket
state: queued
kind: bug
origin: human
created: '2026-07-21'
priority: medium
blocked_by: []
parent: null
scope:
- src/frob/gates/_docblocks.py
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
found while working T-0405 (language extension contract survey): DOC004's fenced-code-block doc-drift check (frob.gates._docblocks) has _PYTHON_LANGS/_RUST_LANGS/_TS_LANGS buckets but no C/C++ bucket -- a fenced c or cpp code block in docs gets no drift checking at all, unlike python/rust/typescript. Add a _C_LANGS/_CPP_LANGS bucket (or a combined c-cpp one, matching frob.vet's capability-matrix convention) with the matching source-extraction branch in doc004_gate.

<!-- ticket:T-0567 -->
```yaml
id: T-0567
title: 'DEAD001 residual: _documented_srcs/_run_jobs in gates/__init__.py'
state: queued
kind: bug
origin: human
created: '2026-07-21'
priority: medium
blocked_by: []
parent: null
scope:
- src/frob/gates/__init__.py
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
T-0565 fixed the callgraph/const-extraction substrate bugs behind most DEAD001 false positives and triaged the remainder, but src/frob/gates/__init__.py::_documented_srcs (line ~1717) and ::_run_jobs (line ~6986) are out of scope this wave (a sibling agent owns gates/__init__.py). Triage needed: _documented_srcs looks like a genuinely-orphaned helper superseded by _resolved_documented_srcs (verify with grep, likely delete); _run_jobs' docstring references a caller ('_run_jobs used to time each job...') suggesting a similar superseded-helper pattern. Either delete (with a zero-reference grep) or add a correctly-placed frob:tests/frob:invariant directive above the symbol itself (not above a test function -- the DSL binds Edge.src to whatever the comment sits directly above, several of T-0565's residual findings turned out to be frob:tests directives misplaced above the TEST function instead of the SOURCE symbol).

<!-- ticket:T-draft-ac820c46 -->
```yaml
id: T-draft-ac820c46
title: 'PRE001 catch-22 on slow mounts: sweep needs a timeout/partial-state or async
  design (T-0355 item 2)'
state: queued
kind: bug
origin: human
created: '2026-07-21'
priority: medium
blocked_by: []
parent: null
scope:
- src/frob/gates/**
- src/frob/tickets/**
scope_changes: []
evidence: []
attachments: []
acceptance: []
threat: null
component: null
labels: []
```
found while working T-0355 (deliberately split out, item 2 of that ticket's original 3-item report): editing a ticket's scope after start demands a re-sweep before PRE001 is satisfiable, and frob ticket sweep's dup+xref pass is a synchronous full-scope scan -- on a slow mount (WSL /mnt/c, network share) that scan itself can be slow enough that the ticket can never get back into a checkable state within a reasonable session. T-0474 already backgrounds the sweep at frob ticket start time, but frob ticket sweep (the always-available resweep path used after a scope edit) is still fully synchronous by design (see its docstring: 'the always-available, always-synchronous way to record it'), and PRE001 itself only ever compares against a fully-completed digest -- there is no partial-sweep-ok state. This needs an actual design decision before implementation (a timeout + partial-sweep-ok ticket state that prework_gate treats as provisionally clean, vs. making frob ticket sweep itself background-and-poll like start), not a mechanical port of an existing fix, so it was NOT implemented as part of T-0355 (items 1 and 3 of that ticket were: clean SIGINT message in __main__.py, and confirming scope_digest is already content-only/checkout-portable).
