---
id: T-0373
title: 'arch gate: read [arch] thresholds from frob.toml (wire the calibrated 800/60,
  not defaults)'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: T-0204
tier: ticket
sprint: null
scope:
- src/frob/gates/_arch.py
- src/frob/arch/
- src/frob/app/config.py
- frob.toml
- docs/modules/arch.md
- pyproject.toml
- CHANGELOG.md
- uv.lock
- tests/unit/test_config.py
- tests/unit/test_arch.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_config.py::test_reads_override
- tests/unit/test_arch.py::TestLargeFile::test_calibrated_frob_toml_threshold_suppresses_600_line_flag
- tests/test_gates.py::TestArchGateThresholds::test_arch_gate_uses_calibrated_default_not_library_default
- tests/test_gates.py::TestArchGateThresholds::test_arch001_respects_explicit_frob_toml_override
designated_repro_test: null
threat: null
component: null
---
The frob-check ARCH stage (gates/_arch.py::arch_gate -> analyze_project(root)) uses arch's DEFAULT thresholds (max_file_lines=500, default function/nesting limits). The user CALIBRATED these to idiomatic values (max_function_lines=60, max_file_lines=800, per frob-rework-state memory) but that calibration only reaches the .frob-release.json  info  large-file
  file has 946 lines (threshold: 500)
tickets-archive.md  info  large-file
  file has 21214 lines (threshold: 500)
CHANGELOG.md  info  large-file
  file has 589 lines (threshold: 500)
uv.lock  info  large-file
  file has 1421 lines (threshold: 500)
coverage.xml  info  large-file
  file has 24935 lines (threshold: 500)
.coverage  info  large-file
  file has 56767 lines (threshold: 500)
tickets.md  info  large-file
  file has 8339 lines (threshold: 500)
.serena/cache/python/document_symbols.pkl  info  large-file
  file has 10754 lines (threshold: 500)
.serena/cache/python/raw_document_symbols.pkl  info  large-file
  file has 8272 lines (threshold: 500)
.playwright-mcp/page-2026-07-20T05-24-03-845Z.yml  info  large-file
  file has 852 lines (threshold: 500)
.playwright-mcp/page-2026-07-20T05-26-02-718Z.yml  info  large-file
  file has 616 lines (threshold: 500)
.playwright-mcp/page-2026-07-20T05-25-43-635Z.yml  info  large-file
  file has 896 lines (threshold: 500)
.playwright-mcp/page-2026-07-20T05-26-18-725Z.yml  info  large-file
  file has 692 lines (threshold: 500)
docs/modules/vet.md  info  large-file
  file has 1136 lines (threshold: 500)
docs/modules/dup.md  info  large-file
  file has 653 lines (threshold: 500)
docs/modules/gates.md  info  large-file
  file has 642 lines (threshold: 500)
docs/modules/dup-sota-survey.md  info  large-file
  file has 648 lines (threshold: 500)
docs/modules/tickets.md  info  large-file
  file has 661 lines (threshold: 500)
docs/strata/surface.md  info  large-file
  file has 859 lines (threshold: 500)
docs/strata/threat.md  info  large-file
  file has 755 lines (threshold: 500)
docs/design/system-design-corpus.md  info  large-file
  file has 995 lines (threshold: 500)
docs/design/compliance-corpus.md  info  large-file
  file has 653 lines (threshold: 500)
docs/design/architecture-check-catalog.md  info  large-file
  file has 1073 lines (threshold: 500)
docs/design/design-pattern-catalog.md  info  large-file
  file has 1062 lines (threshold: 500)
docs/design/cwe-1000-registry.md  info  large-file
  file has 1218 lines (threshold: 500)
docs/design/design-pattern-traps-corpus.md  info  large-file
  file has 1000 lines (threshold: 500)
docs/design/system-performance-corpus.md  info  large-file
  file has 851 lines (threshold: 500)
docs/design/supply-chain-corpus.md  info  large-file
  file has 812 lines (threshold: 500)
docs/design/registry/system-design.yaml  info  large-file
  file has 843 lines (threshold: 500)
docs/design/registry/evasion.yaml  info  large-file
  file has 680 lines (threshold: 500)
docs/design/registry/patterns.yaml  info  large-file
  file has 2427 lines (threshold: 500)
docs/design/registry/weaknesses.yaml  info  large-file
  file has 6927 lines (threshold: 500)
docs/design/registry/arch-checks.yaml  info  large-file
  file has 2182 lines (threshold: 500)
tests/test_gates.py  info  large-file
  file has 3352 lines (threshold: 500)
tests/test_gates.py:428  warning  long-function
  function `TestCoverageGate.test_cov002_stale_done_ticket_unrelated_tickets_md_touch_still_fires` has 34 lines (threshold: 30)
tests/test_gates.py:567  warning  long-function
  function `TestCoverageGate.test_load_tests_merges_python_and_rust_node_ids` has 37 lines (threshold: 30)
tests/test_gates.py:819  warning  long-function
  function `TestScopePrework.test_scope001_exempts_file_committed_by_earlier_ticket` has 36 lines (threshold: 30)
tests/test_gates.py:1268  warning  long-function
  function `TestTestGate.test_test002_satisfied_by_rust_directive_bound_cross_file` has 32 lines (threshold: 30)
tests/test_gates.py:1328  warning  long-function
  function `TestTestGate.test_test001_002_explicit_unit_edge_honored_regardless_of_test_name` has 36 lines (threshold: 30)
tests/test_gates.py:1391  warning  long-function
  function `TestTestGate.test_test003_satisfied_by_parametrized_test_node_id` has 35 lines (threshold: 30)
tests/test_gates.py:1430  warning  long-function
  function `TestTestGate.test_test003_satisfied_by_proptest_macro_block` has 41 lines (threshold: 30)
tests/test_gates.py:1473  warning  long-function
  function `TestTestGate.test_test002_parametrized_test_counts_each_case` has 36 lines (threshold: 30)
tests/test_gates.py:1814  warning  long-function
  function `TestCoverageLoad.test_parses_line_to_symbol_span` has 38 lines (threshold: 30)
tests/test_gates.py:1925  warning  long-function
  function `TestCoverageLoad.test_multi_root_resolves_each_class_to_its_real_root` has 42 lines (threshold: 30)
tests/test_gates.py:2056  warning  long-function
  function `TestRunJobsTimingAttribution.test_cpu_bound_neighbor_does_not_inflate_a_cheap_jobs_timing` has 43 lines (threshold: 30)
tests/test_gates.py:2298  warning  long-function
  function `TestCov002ScopeCoverage.test_open_ticket_scope_covers_changed_symbol` has 40 lines (threshold: 30)
tests/test_gates.py:2356  warning  long-function
  function `TestCov002StrataModuleCoverage.test_module_level_ticket_edge_covers_nested_declaration` has 51 lines (threshold: 30)
tests/test_gates.py:2812  warning  long-function
  function `TestOptInGates.test_dup_gate_planted_clone_waived_passes` has 54 lines (threshold: 30)
tests/test_gates.py:3085  warning  long-function
  function `TestSysGate.test_sys003_import` has 34 lines (threshold: 30)
tests/test_gates.py:255  warning  god-class
  class `TestCoverageGate` has 28 methods (threshold: 12)
tests/test_gates.py:770  warning  god-class
  class `TestScopePrework` has 14 methods (threshold: 12)
tests/test_gates.py:1237  warning  god-class
  class `TestTestGate` has 25 methods (threshold: 12)
tests/test_gates.py:3033  warning  god-class
  class `TestSysGate` has 18 methods (threshold: 12)
tests/test_prework_parity.py:92  warning  long-function
  function `TestCliStartRecordsGateCompatibleDigest.test_start_then_gate_is_clean` has 42 lines (threshold: 30)
tests/test_tickets_collision.py:57  warning  long-function
  function `TestPostArchiveReissueIncident.test_new_ticket_never_reissues_an_archived_id` has 34 lines (threshold: 30)
tests/test_tickets_collision.py:100  warning  long-function
  function `TestTwoCheckoutConcurrentFilingIncident.test_two_worktrees_file_concurrently_no_collision` has 88 lines (threshold: 30)
tests/test_tickets_collision.py:201  warning  long-function
  function `TestSweepWorktreeCollisionIncident.test_renumber_one_rewrites_ledger_and_many_code_references` has 38 lines (threshold: 30)
tests/test_capability_registry.py  info  large-file
  file has 624 lines (threshold: 500)
tests/test_testing.py  info  large-file
  file has 1922 lines (threshold: 500)
tests/test_testing.py:209  warning  long-function
  function `TestSelect.test_reversed_directive_never_selects_the_source_symbol` has 31 lines (threshold: 30)
tests/test_testing.py:519  warning  long-function
  function `TestWorktree.test_select_and_run_in_linked_worktree` has 35 lines (threshold: 30)
tests/test_testing.py:573  warning  long-function
  function `TestCollectPythonTests.test_parses_node_ids_and_caches_on_content_hash` has 32 lines (threshold: 30)
tests/test_testing.py:612  warning  long-function
  function `TestCollectPythonTestsNestedRunner.test_nested_test_runner_cwd_is_collected_and_rerooted` has 63 lines (threshold: 30)
tests/test_testing.py:880  warning  long-function
  function `TestMultipleRunnersPerLanguage.test_routes_each_crate_to_its_own_runner` has 32 lines (threshold: 30)
tests/test_testing.py:971  warning  long-function
  function `TestCollectRustTests._write_crate` has 31 lines (threshold: 30)
tests/test_testing.py:1023  warning  long-function
  function `TestCollectRustTests.test_collect_rust_tests_parses_and_caches` has 40 lines (threshold: 30)
tests/test_testing.py:1076  warning  long-function
  function `TestCollectRustTests.test_collect_rust_tests_skips_lib_less_crate` has 51 lines (threshold: 30)
tests/test_testing.py:1798  warning  long-function
  function `TestCollectBranchGaps.test_collect_python_tests_nested_failure_degrades_with_warning` has 38 lines (threshold: 30)
tests/test_testing.py:1880  warning  long-function
  function `TestCollectBranchGaps.test_run_cargo_test_list_integration_failure_propagates` has 36 lines (threshold: 30)
tests/test_testing.py:270  warning  god-class
  class `TestRunners` has 15 methods (threshold: 12)
tests/test_testing.py:1366  warning  god-class
  class `TestNativeFingerprint` has 13 methods (threshold: 12)
tests/test_testing.py:1550  warning  god-class
  class `TestCollectBranchGaps` has 19 methods (threshold: 12)
tests/test_vet_containment.py:163  warning  long-function
  function `TestFetchCweForCve.test_expired_cache_entry_triggers_a_fresh_fetch` has 46 lines (threshold: 30)
tests/test_vet_containment.py:415  warning  long-function
  function `TestRenderContainmentReport.test_unverified_sorts_between_live_and_contained` has 43 lines (threshold: 30)
tests/test_clipboard.py  info  large-file
  file has 587 lines (threshold: 500)
tests/test_clipboard.py:86  warning  long-function
  function `TestBackends.test_wsl_detection_via_proc_version` has 32 lines (threshold: 30)
tests/test_clipboard.py:401  warning  long-function
  function `TestBackends.test_wsl_has_image_true_and_false` has 31 lines (threshold: 30)
tests/test_clipboard.py:28  warning  god-class
  class `TestBackends` has 25 methods (threshold: 12)
tests/test_secrets_gate.py  info  large-file
  file has 624 lines (threshold: 500)
tests/test_secrets_gate.py:164  warning  god-class
  class `TestFakeMarking` has 13 methods (threshold: 12)
tests/test_ticket_land.py  info  large-file
  file has 1135 lines (threshold: 500)
tests/test_ticket_land.py:475  warning  long-function
  function `TestDraftFinalizeRewritesCodeAndLeavesWorktreeClean.test_code_directive_rewritten_and_worktree_clean_after_land` has 37 lines (threshold: 30)
tests/test_ticket_land.py:526  warning  long-function
  function `TestArchiveResurrection.test_archived_id_never_resurrected` has 51 lines (threshold: 30)
tests/test_ticket_land.py:1072  warning  long-function
  function `TestPreworkSweepRefresh.test_land_refreshes_stale_sweep_after_unrelated_main_change` has 33 lines (threshold: 30)
tests/test_lang.py:158  warning  god-class
  class `TestParseTsRustCppC` has 15 methods (threshold: 12)
tests/test_vet.py  info  large-file
  file has 2061 lines (threshold: 500)
tests/test_vet.py:1147  warning  long-function
  function `TestFingerprintScan.test_self_pattern_exclusion_covers_every_needle_table_module` has 38 lines (threshold: 30)
tests/test_vet.py:1201  warning  long-function
  function `TestFingerprintScan.test_self_pattern_exclusion_survives_a_foreign_install_copy` has 31 lines (threshold: 30)
tests/test_vet.py:1705  warning  long-function
  function `TestScanTreeTimeout.test_slow_package_returns_within_timeout_not_task_duration` has 38 lines (threshold: 30)
tests/test_vet.py:372  warning  god-class
  class `TestCapabilityScan` has 24 methods (threshold: 12)
tests/test_vet.py:995  warning  god-class
  class `TestFingerprintScan` has 20 methods (threshold: 12)
tests/test_tickets.py  info  large-file
  file has 999 lines (threshold: 500)
tests/test_tickets.py:785  warning  long-function
  function `TestSingleFileLedger.test_migrate_collapses_dir_into_ledger` has 33 lines (threshold: 30)
tests/test_tickets.py:218  warning  god-class
  class `TestStateMachine` has 13 methods (threshold: 12)
tests/test_fuzz.py  info  large-file
  file has 506 lines (threshold: 500)
tests/test_graph.py  info  large-file
  file has 1264 lines (threshold: 500)
tests/test_graph.py:678  warning  long-function
  function `TestExclude.test_walk_source_files_prunes_before_descent` has 31 lines (threshold: 30)
tests/test_graph.py:927  warning  long-function
  function `TestCorruptCacheRecovery.test_ddl_failure_after_connect_probe_passes_is_recovered` has 39 lines (threshold: 30)
tests/test_graph.py:1019  warning  long-function
  function `TestCacheModule.test_store_and_load_file_data_roundtrip` has 44 lines (threshold: 30)
tests/test_graph.py:1070  warning  long-function
  function `TestCacheModule.test_connect_readonly_rejects_writes_no_lock_contention` has 31 lines (threshold: 30)
tests/test_graph.py:1142  warning  long-function
  function `TestConcurrentCache.test_connect_on_current_schema_does_not_block_on_a_held_write_lock` has 42 lines (threshold: 30)
tests/test_graph.py:149  warning  god-class
  class `TestDsl` has 21 methods (threshold: 12)
tests/test_perf.py  info  large-file
  file has 594 lines (threshold: 500)
tests/integration/test_integration.py:109  suggestion  deep-nesting
  function `test_cycle_detected_in_mini_project` has nesting depth 5 (threshold: 4)
tests/integration/test_interfaces.py:52  warning  god-class
  class `TestInterfaces` has 13 methods (threshold: 12)
tests/system/test_cli_ticket.py:138  warning  long-function
  function `TestTicketRoundTrip.test_close_with_evidence_and_done_report_succeeds` has 31 lines (threshold: 30)
tests/system/test_cli_sys_plan.py:103  warning  long-function
  function `TestSysPlanCli.test_dropped_ticket_is_not_recreated` has 33 lines (threshold: 30)
tests/system/test_frob_self_model.py:117  warning  long-function
  function `TestFrobSelfModel.test_every_claim_proves` has 59 lines (threshold: 30)
tests/system/test_cli_check.py  info  large-file
  file has 605 lines (threshold: 500)
tests/system/test_cli_check.py:329  warning  long-function
  function `TestCheckDocAnchorScopedVsUnscoped.test_scoped_docanchor_matches_unscoped` has 37 lines (threshold: 30)
tests/system/test_cli_ticket_land.py:32  warning  long-function
  function `TestLandCLI.test_dry_run_reports_clean` has 62 lines (threshold: 30)
tests/unit/test_logging_quiet.py:46  warning  long-function
  function `TestQuietStdoutLogsReentrance.test_interleaved_enter_exit_across_threads_never_sticks` has 33 lines (threshold: 30)
tests/unit/test_arch.py  info  large-file
  file has 527 lines (threshold: 500)
tests/unit/test_arch.py:280  warning  long-function
  function `TestDispatchFamilySuppression.test_accidental_same_signature_still_flagged` has 32 lines (threshold: 30)
tests/unit/test_arch.py:318  warning  long-function
  function `TestDispatchFamilySuppression.test_init_reexport_does_not_suppress` has 41 lines (threshold: 30)
tests/unit/test_arch.py:367  warning  long-function
  function `TestDispatchFamilySuppression.test_test_file_co_mention_does_not_suppress` has 46 lines (threshold: 30)
tests/unit/test_app_runners_batch5.py  info  large-file
  file has 842 lines (threshold: 500)
tests/unit/test_app_runners_batch5.py:152  warning  long-function
  function `TestDupRunner.test_probe_equivalent_exits_0` has 34 lines (threshold: 30)
tests/unit/test_app_runners_batch5.py:188  warning  long-function
  function `TestDupRunner.test_probe_differ_exits_1` has 34 lines (threshold: 30)
tests/unit/test_app_runners_batch5.py:224  warning  long-function
  function `TestDupRunner.test_probe_err_result_exits_1` has 31 lines (threshold: 30)
tests/unit/test_app_runners_batch5.py:717  warning  long-function
  function `TestVetRunner.test_scan_with_violations_enforced_exits_1` has 36 lines (threshold: 30)
tests/unit/test_app_runners_batch5.py:755  warning  long-function
  function `TestVetRunner.test_scan_with_cve_matches_text_mode` has 61 lines (threshold: 30)
tests/unit/test_parse.py  info  large-file
  file has 1088 lines (threshold: 500)
tests/unit/test_parse.py:85  warning  god-class
  class `TestToolResult` has 14 methods (threshold: 12)
tests/unit/test_parse.py:234  warning  god-class
  class `TestParsePytest` has 21 methods (threshold: 12)
tests/unit/test_parse.py:525  warning  god-class
  class `TestParseTy` has 17 methods (threshold: 12)
tests/unit/test_parse.py:635  warning  god-class
  class `TestParseClang` has 15 methods (threshold: 12)
tests/unit/test_parse.py:770  warning  god-class
  class `TestParseJunit` has 19 methods (threshold: 12)
tests/unit/test_app_runners_batch6.py  info  large-file
  file has 725 lines (threshold: 500)
tests/unit/test_app_runners_batch6.py:220  warning  long-function
  function `TestGraphRunner.test_why_acked_stale_dangling_render_lines` has 39 lines (threshold: 30)
tests/unit/test_app_runners_batch6.py:46  warning  god-class
  class `TestGraphRunner` has 16 methods (threshold: 12)
tests/unit/test_app_runners_batch6.py:264  warning  god-class
  class `TestPerfRunner` has 14 methods (threshold: 12)
tests/unit/test_app_runners_batch6.py:510  warning  god-class
  class `TestCheckRunner` has 15 methods (threshold: 12)
tests/unit/test_app_runners_batch7.py  info  large-file
  file has 1156 lines (threshold: 500)
tests/unit/test_check.py:224  warning  long-function
  function `TestSummarySeverityHonesty.test_warn_only_gate_summary_splits_errors_and_warnings` has 33 lines (threshold: 30)
tests/unit/test_check.py:307  warning  long-function
  function `TestCollectResultsLogLevelRace.test_racing_tasks_restore_original_stdout_handler_level` has 40 lines (threshold: 30)
tests/unit/strata/test_litmus_payments.py:46  warning  long-function
  function `_payments_model` has 107 lines (threshold: 30)
tests/unit/strata/test_kernel_properties.py:123  suggestion  deep-nesting
  function `_bfs_oracle` has nesting depth 5 (threshold: 4)
tests/unit/strata/test_litmus_waive.py:84  warning  long-function
  function `TestWaiveLitmus.test_sub_target_waiver_does_not_suppress_a_different_sub_target` has 47 lines (threshold: 30)
tests/unit/strata/test_secrets.py:158  warning  long-function
  function `TestAgePropagationReuse.test_lifetime_joins_existing_age_bound_claim` has 35 lines (threshold: 30)
tests/unit/strata/test_secrets.py:267  warning  long-function
  function `TestReadersExactSetClosure.test_readers_claim_refutes_across_a_declassify_boundary` has 38 lines (threshold: 30)
tests/unit/strata/test_deploy.py:75  warning  long-function
  function `TestEndorsementChainValidation.test_non_endorse_boundary_fails_closed` has 31 lines (threshold: 30)
tests/unit/strata/test_deploy.py:171  warning  long-function
  function `TestAutoGeneratedScenarios.test_canary_and_rollback_scenarios_re_check_every_declared_claim` has 33 lines (threshold: 30)
tests/unit/strata/test_refine.py:73  warning  long-function
  function `TestRefineHappyPath.test_noflow_claim_proved_at_abstract_level_stays_proved_after_refinement` has 38 lines (threshold: 30)
tests/unit/strata/test_infra.py:68  warning  long-function
  function `TestCacheDesugar.test_cache_node_and_fill_flow` has 33 lines (threshold: 30)
tests/unit/strata/test_selfconform.py  info  large-file
  file has 1034 lines (threshold: 500)
tests/unit/strata/test_selfconform.py:190  warning  long-function
  function `TestUndeclaredInterfaceCrossPassDedup.test_same_site_observed_by_both_passes_yields_one_finding` has 31 lines (threshold: 30)
tests/unit/strata/test_selfconform.py:884  warning  long-function
  function `TestWaiverChannel.test_matching_waiver_moves_violation_to_waived` has 37 lines (threshold: 30)
tests/unit/strata/test_selfconform.py:951  warning  long-function
  function `TestWaiverChannel.test_sub_target_waiver_does_not_suppress_a_different_kind` has 38 lines (threshold: 30)
tests/unit/strata/test_litmus_waive_store.py:82  warning  long-function
  function `TestWaiveStoreLitmus.test_store_sub_target_waiver_does_not_suppress_a_different_sub_target` has 44 lines (threshold: 30)
tests/unit/strata/test_threat.py  info  large-file
  file has 1218 lines (threshold: 500)
tests/unit/strata/test_threat.py:702  warning  long-function
  function `TestMitigationKindChokepoint.test_mixed_paths_matching_on_one_wrong_kind_on_other_does_not_discharge` has 40 lines (threshold: 30)
tests/unit/strata/test_observe.py:103  warning  long-function
  function `TestEndToEnd.test_phases_operation_and_observe_together` has 38 lines (threshold: 30)
tests/unit/strata/test_parse.py:12  warning  god-class
  class `TestParseModule` has 14 methods (threshold: 12)
tests/unit/strata/test_elaborate.py:24  warning  long-function
  function `TestElaborateFullMapping.test_maps_every_construct_field_for_field` has 69 lines (threshold: 30)
tests/unit/strata/test_elaborate.py:391  warning  long-function
  function `TestElaborateEndToEnd.test_parse_elaborate_evaluate_matches_expected_verdicts` has 36 lines (threshold: 30)
tests/unit/strata/test_lint.py  info  large-file
  file has 587 lines (threshold: 500)
tests/unit/strata/test_sysdoc.py:75  warning  long-function
  function `TestRenderAuditMatrix.test_assumed_discharge_renders_distinct_from_proved` has 34 lines (threshold: 30)
tests/unit/strata/test_capacity.py:146  warning  long-function
  function `TestSkewUtilization.test_skew_refutes_where_mean_would_prove` has 35 lines (threshold: 30)
tests/unit/strata/test_audit.py:188  warning  long-function
  function `_hardened_model` has 33 lines (threshold: 30)
tests/unit/strata/test_audit.py:301  warning  long-function
  function `_isolated_hardened_two_user_model` has 32 lines (threshold: 30)
tests/unit/strata/test_audit.py:347  warning  long-function
  function `TestGroupGaps.test_group_gaps_by_view` has 46 lines (threshold: 30)
tests/unit/cve/test_parser.py:201  warning  long-function
  function `test_cve_module_end_to_end_over_mirror` has 31 lines (threshold: 30)
tests/unit/cve/fixtures/CVE-2024-3094.json  info  large-file
  file has 568 lines (threshold: 500)
tests/unit/cve/fixtures/CVE-2021-44228.json  info  large-file
  file has 796 lines (threshold: 500)
tests/unit/cve/fixtures/mirror/cves/2024/3xxx/CVE-2024-3094.json  info  large-file
  file has 568 lines (threshold: 500)
tests/unit/cve/fixtures/mirror/cves/2021/44xxx/CVE-2021-44228.json  info  large-file
  file has 796 lines (threshold: 500)
tests/unit/deploy/test_vm_runner.py:52  warning  long-function
  function `_fake_subprocess_run` has 33 lines (threshold: 30)
tests/unit/graph/test_dsl.py:289  warning  long-function
  function `TestBlockBinding.test_narrow_following_window_propagates_backward_through_run` has 36 lines (threshold: 30)
src/frob/__main__.py  info  large-file
  file has 1279 lines (threshold: 500)
src/frob/__main__.py:840  warning  long-function
  function `_add_vet_parser` has 40 lines (threshold: 30)
src/frob/gates/_secrets.py  info  large-file
  file has 669 lines (threshold: 500)
src/frob/gates/_secrets.py:443  warning  long-function
  function `_looks_low_entropy` has 40 lines (threshold: 30)
src/frob/gates/__init__.py  info  large-file
  file has 4047 lines (threshold: 500)
src/frob/gates/__init__.py:413  warning  long-function
  function `_case_count` has 41 lines (threshold: 30)
src/frob/gates/__init__.py:1017  warning  long-function
  function `_cov001` has 45 lines (threshold: 30)
src/frob/gates/__init__.py:1988  warning  long-function
  function `_test009` has 42 lines (threshold: 30)
src/frob/gates/__init__.py:3825  warning  long-function
  function `_build_jobs` has 36 lines (threshold: 30)
src/frob/gates/_prework.py:174  warning  long-function
  function `sweep_ticket` has 66 lines (threshold: 30)
src/frob/testing/_collect.py  info  large-file
  file has 675 lines (threshold: 500)
src/frob/testing/_collect.py:143  warning  long-function
  function `_native_artifact_digest` has 39 lines (threshold: 30)
src/frob/testing/_collect.py:368  warning  long-function
  function `collect_python_tests` has 46 lines (threshold: 30)
src/frob/testing/_runners.py  info  large-file
  file has 546 lines (threshold: 500)
src/frob/check/_python.py  info  large-file
  file has 569 lines (threshold: 500)
src/frob/check/_python.py:499  warning  long-function
  function `_exports_for_package` has 35 lines (threshold: 30)
src/frob/check/__init__.py  info  large-file
  file has 585 lines (threshold: 500)
src/frob/perf/_rules.py  info  large-file
  file has 646 lines (threshold: 500)
src/frob/perf/_rules.py:385  warning  long-function
  function `_operand_names` has 37 lines (threshold: 30)
src/frob/vet/_capability.py  info  large-file
  file has 1494 lines (threshold: 500)
src/frob/vet/_capability.py:324  warning  long-function
  function `_embedded_capabilities` has 32 lines (threshold: 30)
src/frob/vet/_capability.py:762  warning  long-function
  function `_build_py_alias_table` has 32 lines (threshold: 30)
src/frob/vet/_capability.py:1131  warning  long-function
  function `scan_file_operations` has 41 lines (threshold: 30)
src/frob/vet/_scan.py  info  large-file
  file has 772 lines (threshold: 500)
src/frob/vet/_capability_registry.py  info  large-file
  file has 1862 lines (threshold: 500)
src/frob/vet/_closedworld.py:71  warning  long-function
  function `walk_python_imports` has 31 lines (threshold: 30)
src/frob/vet/_closedworld.py:176  warning  long-function
  function `resolve_import` has 69 lines (threshold: 30)
src/frob/vet/_closedworld.py:257  warning  long-function
  function `closed_world_accounting` has 33 lines (threshold: 30)
src/frob/vet/_cve.py  info  large-file
  file has 502 lines (threshold: 500)
src/frob/strata/_ast.py  info  large-file
  file has 677 lines (threshold: 500)
src/frob/strata/_models.py  info  large-file
  file has 579 lines (threshold: 500)
src/frob/strata/_compliance.py  info  large-file
  file has 794 lines (threshold: 500)
src/frob/strata/_audit.py  info  large-file
  file has 816 lines (threshold: 500)
src/frob/strata/_audit.py:376  warning  long-function
  function `_evaluate_family` has 35 lines (threshold: 30)
src/frob/strata/_selfconform.py  info  large-file
  file has 756 lines (threshold: 500)
src/frob/strata/_selfconform.py:369  warning  long-function
  function `_extended_kind_violations` has 40 lines (threshold: 30)
src/frob/strata/_selfconform.py:433  warning  long-function
  function `_fully_excluded_node_ids` has 37 lines (threshold: 30)
src/frob/strata/_threat.py  info  large-file
  file has 1606 lines (threshold: 500)
src/frob/strata/_threat.py:290  warning  long-function
  function `load_repo_benign_capabilities` has 60 lines (threshold: 30)
src/frob/strata/_threat.py:972  warning  long-function
  function `check_capability_completeness` has 36 lines (threshold: 30)
src/frob/strata/_native_staleness.py:131  warning  long-function
  function `stale_natives` has 46 lines (threshold: 30)
src/frob/strata/_host.py:237  warning  long-function
  function `host_manifest_for` has 36 lines (threshold: 30)
src/frob/strata/__init__.py  info  large-file
  file has 504 lines (threshold: 500)
src/frob/strata/_host_isolation.py  info  large-file
  file has 893 lines (threshold: 500)
src/frob/strata/_elaborate.py  info  large-file
  file has 1382 lines (threshold: 500)
src/frob/strata/_infra.py  info  large-file
  file has 794 lines (threshold: 500)
src/frob/strata/_infra.py:110  warning  long-function
  function `_elaborate_store` has 31 lines (threshold: 30)
src/frob/strata/_infra.py:156  warning  long-function
  function `_store_base_attrs` has 31 lines (threshold: 30)
src/frob/strata/_claims.py  info  large-file
  file has 720 lines (threshold: 500)
src/frob/arch/_python.py:313  warning  long-function
  function `_collect_dispatch_refs` has 50 lines (threshold: 30)
src/frob/arch/_python.py:381  warning  long-function
  function `_is_dispatch_family` has 32 lines (threshold: 30)
src/frob/arch/_python.py:313  suggestion  deep-nesting
  function `_collect_dispatch_refs` has nesting depth 6 (threshold: 4)
src/frob/arch/__init__.py:165  warning  long-function
  function `_analyze_one_file` has 52 lines (threshold: 30)
src/frob/deploy/_conform.py  info  large-file
  file has 542 lines (threshold: 500)
src/frob/tickets/_land.py  info  large-file
  file has 946 lines (threshold: 500)
src/frob/tickets/_land.py:434  warning  long-function
  function `land` has 31 lines (threshold: 30)
src/frob/tickets/_land.py:906  warning  long-function
  function `_land_squash_apply` has 32 lines (threshold: 30)
src/frob/tickets/__init__.py  info  large-file
  file has 1183 lines (threshold: 500)
src/frob/dup/_pipeline.py  info  large-file
  file has 2206 lines (threshold: 500)
src/frob/dup/_pipeline.py:525  warning  long-function
  function `_substitute_calls` has 45 lines (threshold: 30)
src/frob/dup/_pipeline.py:582  warning  long-function
  function `_splice_call_site` has 34 lines (threshold: 30)
src/frob/dup/_pipeline.py:1012  warning  long-function
  function `_fingerprint_symbol` has 35 lines (threshold: 30)
src/frob/dup/_template.py:91  warning  long-function
  function `build_group_template` has 76 lines (threshold: 30)
src/frob/graph/dsl.py:131  warning  long-function
  function `_parse_attrs` has 36 lines (threshold: 30)
src/frob/graph/dsl.py:172  warning  long-function
  function `_parse_line` has 33 lines (threshold: 30)
src/frob/graph/dsl.py:216  warning  long-function
  function `_fold_continuations` has 71 lines (threshold: 30)
src/frob/graph/dsl.py:292  warning  long-function
  function `_resolve_block_srcs` has 44 lines (threshold: 30)
src/frob/graph/callgraph.py:116  suggestion  deep-nesting
  function `_resolve_call_edges` has nesting depth 5 (threshold: 4)
src/frob/graph/__init__.py  info  large-file
  file has 508 lines (threshold: 500)
src/frob/graph/__init__.py:387  warning  long-function
  function `load_graph` has 48 lines (threshold: 30)
src/frob/graph/cache.py:175  warning  long-function
  function `_check_fingerprint` has 37 lines (threshold: 30)
src/frob/app/stats_runner.py:17  warning  long-function
  function `run` has 33 lines (threshold: 30)
src/frob/app/config.py  info  large-file
  file has 515 lines (threshold: 500)
src/frob/app/ticket_runner.py  info  large-file
  file has 806 lines (threshold: 500)
src/frob/app/ticket_runner.py:688  warning  long-function
  function `_apply_evidence` has 50 lines (threshold: 30)
src/frob/app/sys_runner.py  info  large-file
  file has 678 lines (threshold: 500)
frob-core/src/lib.rs  info  large-file
  file has 1349 lines (threshold: 500)
design/frob.strata  info  large-file
  file has 520 lines (threshold: 500)
strata-core/src/lib.rs  info  large-file
  file has 852 lines (threshold: 500)
strata-core/src/parse.rs  info  large-file
  file has 3580 lines (threshold: 500)
tests/test_release.py  suggestion  abstraction-opportunity
  128 functions share signature `(Path)`: _snap, _snap, _snapshot, _boom, _snap, _fake_parse_file, _snapshot, _snapshot, _snapshot, _snapshot, _snapshot, _snapshot, test_load_and_match_globs, test_absent_config_is_empty, test_malformed_toml_is_empty_not_raise, test_exclude_not_a_list_is_empty, test_exclude_list_with_non_string_entry_is_empty, test_dup_scanner_honors_exclude, test_is_nested_worktree_detects_own_git_dir, test_is_nested_worktree_git_file_form, test_is_nested_worktree_false_for_root_itself, test_is_nested_worktree_false_for_plain_subdir, test_should_prune_dir_covers_all_three_signals, _parse, test_put_then_get_returns_same_payload, test_get_miss_returns_none, test_different_rungs_do_not_clobber_each_other, test_same_digest_and_rung_overwrites_prior_payload, test_put_then_get_returns_same_payload, test_lookup_is_order_independent, test_get_miss_returns_none, test_repeated_calls_reuse_one_connection, test_close_all_drops_cached_connections, _boom_unlink, _py_tree, _cpp_tree, test_leaf_tokens_are_formatting_insensitive, test_span_of_is_one_based_inclusive, test_child_text_decodes_and_tolerates_none, test_child_by_field_and_node_text_public_wrappers, test_leading_doc_comment_gathers_block, test_export_tree_and_flatten_tree_round_trip, test_iter_cpp_functions_finds_free_and_member, test_cpp_function_nodes_public_wrapper, test_raw_tree_returns_tree_source_language, test_symbol_tree_covers_span, test_extract_imports_tree_and_path, test_iter_identifiers_tree_and_path, test_resolve_local_import_maps_to_repo_relative, test_observes_net_fs_exec_effects_in_bound_code, test_foreign_files_are_not_scanned, test_declared_may_capability_silences_matching_effect, test_effect_with_no_matching_may_is_a_violation, test_declared_may_of_different_kind_does_not_cover_effect, test_foreign_code_is_not_checked, test_fs_write_effect_needs_fs_kind_declaration, test_core_undeclared_interface_fires, test_core_undeclared_interface_discharges_once_declared, test_extended_undeclared_interface_fires, test_extended_undeclared_interface_discharges_once_declared, test_broad_fs_declaration_discharges_read_only_observation, test_narrow_fs_read_declaration_does_not_cover_fs_read, test_fs_read_only_declaration_still_fires_on_fs_write_observation, test_stale_design_fires, test_stale_design_discharges_once_observed, test_legacy_fs_declaration_discharges_on_read_only_observation, test_fs_read_declaration_discharges_on_read_only_observation, test_fs_read_declaration_stays_stale_when_only_writes_observed, test_stale_design_skips_node_fully_within_graph_exclude, test_stale_design_still_fires_when_node_has_non_excluded_file, test_unmodeled_code_fires, test_unmodeled_code_discharges_once_mapped, test_typescript_undeclared_capability_fires, test_typescript_undeclared_capability_discharges_once_declared, test_typescript_stale_design_fires, test_sorted_capability_files_includes_typescript, test_sorted_capability_files_honors_graph_exclude, test_typescript_core_net_undeclared_fires, test_typescript_core_net_discharges_once_declared, test_rust_core_exec_undeclared_fires, test_rust_core_exec_discharges_once_declared, test_observed_extended_kinds_by_node_only_ever_yields_extended_kinds, test_matching_waiver_moves_violation_to_waived, test_stale, test_sub_target_waiver_does_not_suppress_a_different_kind, test_ambiguous_code_binding_propagates_as_err, test_missing_frob_toml_is_ok_empty, test_missing_strata_table_is_ok_empty, test_declared_entry_is_loaded, test_missing_reason_is_malformed, test_blank_reason_is_malformed, test_unparseable_toml_is_malformed, test_repo_declared_excuse_resolves_threat002, test_binding_and_root_wire_in_threat004_and_threat005, test_undeclared_sink_is_threat004, test_declared_capability_silences_threat004, test_unclassified_sink_kind_is_threat005, test_benign_capability_excuses_threat005, test_classified_sink_with_declared_capability_is_clean, test_foreign_code_is_not_joined, test_non_default_catalog_moves_the_sink_taxonomy_with_it, test_partitions_files_by_glob_and_defaults_unmatched_to_foreign, test_graph_exclude_dir_is_never_bound_even_when_glob_matches, test_no_code_glob_declared_yields_empty_binding, test_file_matched_by_two_globs_is_ambiguous, test_same_component_import_is_fine, test_cross_component_import_with_declared_flow_is_fine, test_cross_component_import_without_declared_flow_is_a_violation, test_declared_flow_in_reverse_direction_only_still_refuses_the_import, test_declared_flow_in_exact_direction_satisfies_conformance, test_import_into_foreign_code_is_flagged, test_third_party_import_is_not_tracked, test_from_import_is_resolved_and_checked, test_level1_relative_import_same_package_is_fine, test_level1_relative_import_crossing_component_is_flagged, test_level2_relative_import_crossing_component_is_flagged, test_level2_relative_import_with_declared_flow_is_fine, _walk, _walk, _fuzz_enforce, _build_import_graph, _load_snapshot, build_server, _walk, _load_snapshot, _load_lock_for_ack, _load_test_snapshot, _snapshot
  Consider a shared protocol or base class
tests/test_release.py  suggestion  abstraction-opportunity
  22 functions share signature `(Path, str) -> None`: _write, _commit, _git, _commit, _git_init, _commit_all, _git, _commit, _git, _commit, _git_init, _commit_all, _make_closeable, _git, _commit, test_old_package_passes, test_fresh_package_blocks, _commit_all, _write_frob_toml, _warn_if_native_stale, _run_hook, _maybe_attach_clipboard_image
  Consider a shared protocol or base class
tests/test_stats.py  suggestion  abstraction-opportunity
  27 functions share signature `(Path) -> Path`: _repo, _make_repo, _make_fake_frob_repo_root, _site_packages, _tree, _tree_with_malformed_directive, _setup_repo, _init_repo, _init_repo_with_bound_test, _init_repo, _init_no_design_repo, _init_repo, _init_repo, _setup_repo, _make_polyglot_project, _make_py_project, _write_clean_deploy, _repo_root_for, decisions_dir, _invariants_dir, _display_path, tickets_dir, ledger_path, archive_path, manifest_path, _db_path, _repo_root_for
  Consider a shared protocol or base class
tests/test_decisions.py  suggestion  abstraction-opportunity
  8 functions share signature `(Path, str, str) -> None`: _record, _member_crate, _write, _write, _write, _write, _cache_set, _cache_set
  Consider a shared protocol or base class
tests/test_gates.py  suggestion  abstraction-opportunity
  15 functions share signature `(Path, str, str) -> Path`: _write, _write, _write, _write, _write, _write, _write, _write, _write, _write, _write, _write, _make_project, _write, _write
  Consider a shared protocol or base class
tests/test_gates.py  suggestion  abstraction-opportunity
  823 functions share signature `(Path) -> None`: _git_init, test_drift001_stale_ack_has_remedy, test_drift002_dangling_has_candidates, test_no_drift_when_clean, test_stamp_and_load_round_trip, test_load_baseline_missing_is_none, test_delta_filters_known_violations, test_baseline_not_stale_when_files_unchanged, test_baseline_stale_when_file_changes, test_cov001_broken_doc_edge_does_not_suppress_finding, test_cov001_undocumented_public_symbol, test_cov001_message_wording_for_docstring_without_doc_edge, test_cov001_passes_when_documented, test_cov001_exempts_generated_file_with_marker, test_cov001_still_fires_without_generated_marker, test_cov002_unticketed_diff_hunk, test_cov002_passes_with_open_ticket_edge, test_cov002_done_ticket_covers_own_closing_diff, test_cov002_done_ticket_without_grace_still_fires, test_cov002_stale_done_ticket_unrelated_tickets_md_touch_still_fires, test_cov003_done_ticket_missing_evidence, test_cov003_names_unbuilt_native_as_remedy, test_cov003_honest_remedy_when_no_native_missing, test_cov003_passes_when_evidence_collected, test_cov003_passes_for_rust_evidence_id, test_load_tests_merges_python_and_rust_node_ids, test_cov004_missing_attachment, test_todo001_unbound_directive, test_todo001_bare_comment_in_touched_file, test_waiver_suppresses_and_reports, test_waive001_missing_reason, test_waive002_known_gate_rule_is_not_flagged, test_waive002_flags_arch_category_as_ineffective, test_waive002_does_not_flag_arch001_as_ineffective, test_waive002_flags_unknown_rule_id_as_ineffective, test_waive002_honors_loaded_policy_rule_ids, test_waive002_end_to_end_via_run_gates, test_scope001_out_of_scope_file, test_scope001_passes_in_scope, test_scope_unrestricted_when_no_scope_declared, test_scope001_comma_joined_entry_splits_and_matches, test_scope001_dir_prefix_globs_recursively, test_scope001_ledger_implicitly_in_scope, test_scope001_exempts_file_committed_by_earlier_ticket, test_scope001_still_flags_uncommitted_out_of_scope_edit, test_scope001_does_not_exempt_when_referenced_ticket_lacks_scope, test_pre001_missing_sweep, test_pre001_passes_with_current_sweep, test_pre001_stale_sweep, test_prework_skips_when_not_in_progress, test_record_and_load_prework_roundtrip, test_sweep_ticket_honors_graph_excludes, test_sweep_ticket_skips_builtin_skip_dirs, test_sweep_ticket_xref_hits_are_real_symbols, test_explicit_flag_wins, test_branch_regex_match, test_nothing_fallback, test_inv001_no_evidence, test_inv001_uncollected_node_id, test_inv001_passes_with_collected_evidence, test_inv002_no_anchor, test_inv001_evidence_via_policy_rule_id, test_malformed_bad_id, test_duplicate_id, test_missing_directory_ok, test_loads_valid, test_no_frontmatter_block_is_malformed, test_bad_yaml_frontmatter_is_malformed, test_non_mapping_frontmatter_is_malformed, test_empty_statement_is_malformed, test_evidence_not_a_list_is_malformed, test_bad_criticality_is_malformed, test_test001_public_symbol_no_unit_edge, test_test002_below_min_unit_cases, test_test002_satisfied_by_rust_directive_bound_cross_file, test_test002_rust_directive_from_non_test_symbol_does_not_satisfy, test_test001_002_explicit_unit_edge_honored_regardless_of_test_name, test_test003_interface_without_integration, test_test003_exempts_strata_design_files, test_test003_satisfied_by_parametrized_test_node_id, test_test003_satisfied_by_proptest_macro_block, test_test002_parametrized_test_counts_each_case, test_test003_waiver_in_a_file_under_the_package_matches, test_test004_system_below_min_e2e, test_test004_passes_with_enough_e2e, test_test005_unit_branch_floor, test_test005_skips_test_file_symbols, test_test005_module_line_floor, test_test005_system_line_floor, test_test008_fires_on_unjoined_root, test_test008_silent_when_root_joined, test_test008_cannot_be_waived, test_test006_missing_stamp, test_test006_stale_stamp, test_edge_with_uncollected_node_id_does_not_satisfy, test_missing_coverage_xml, test_malformed_coverage_xml, test_parses_line_to_symbol_span, test_joins_via_repo_relative_source, test_multi_source_picks_the_root_that_joins, test_multi_root_resolves_each_class_to_its_real_root, test_zero_join_is_loud_not_silent, test_stamp_coverage_roundtrip, test_run_gates_end_to_end, test_run_gates_skips_scope_without_ticket, _init_repo, test_module_level_ticket_edge_covers_nested_declaration, test_declaration_without_module_edge_still_fires, test_invalid_kind_reported, test_valid_kind_not_reported, test_dangling_tests_endpoint_still_caught_by_drift002, test_dup_gate_off_by_default, test_dup_gate_fires_on_planted_clone_when_enabled, test_dup_gate_planted_clone_waived_passes, test_fuzz_gate_off_by_default, test_perf_gate_flags_list_membership_in_loop, test_digest_is_stable_and_scope_sensitive, test_non_matching_scope_is_empty_hash, test_gates_run_gates_integration, test_noop_no_design_dir, test_sys001_dangling, test_sys001_valid, test_sys002_unbound, test_sys002_bound, test_sys003_import, test_sys004_load_failure, test_sys004_suppresses_sys001, test_doc003_proved_claim_passes, test_doc003_refutes_names_obligations, test_doc003_unclaimed_view_ignored, test_doc003_unknown_view, test_doc003_marker_in_fenced_block_ignored, test_doc003_marker_in_inline_code_ignored, test_doc003_real_marker_with_fenced_example_extracts_once, _init_repo, test_main_checkout, test_linked_worktree_resolves_to_worktree_root, test_not_a_repo, test_nonexistent_path_is_not_a_repo, test_covers_committed_staged_unstaged_and_untracked, test_merge_base_not_head, test_hunk_paths_are_repo_relative_posix, test_bad_base_ref_is_git_failed, test_captures_stdout_and_zero_returncode, test_nonzero_returncode_is_ok_not_err, test_nonexistent_binary_is_git_failed, test_timeout_is_git_failed, test_returns_branch_name, test_new_ticket_never_reissues_an_archived_id, test_two_worktrees_file_concurrently_no_collision, test_renumber_one_rewrites_ledger_and_many_code_references, test_dry_run_reports_without_writing, test_remote_symbolic_ref_wins_over_local_main, test_no_remote_falls_back_to_local_master, test_no_remote_no_main_no_master_falls_back_to_main_literal, test_detached_head_is_treated_as_default, test_non_git_directory_is_treated_as_default, _git_init, test_registers_all_five_tools, test_run_delegates_to_run_stdio_with_resolved_root, test_lists_queued_ticket, test_empty_queue_is_empty_list, test_clean_snapshot_has_no_drift, test_dangling_edge_reported, test_stale_ack_reported, test_in_scope_diff_passes, test_out_of_scope_diff_flagged, test_resolves_symbol_and_edges, test_unknown_symbol_is_err, test_reports_doc_edge, test_unknown_symbol_is_err, test_bug_kind_rejected, test_bug_kind_ticket_cannot_close_on_cmd_evidence_alone, test_feature_kind_ticket_rejected, test_security_kind_ticket_rejected, test_docs_kind_closes, test_docs_kind_ticket_failing_cmd_blocks_close, test_records_cmd_evidence_on_docs_ticket, test_requires_ids_or_cmd, test_close_on_queued_exits_nonzero, test_docs_ticket_closed_via_evidence_cmd_is_gate_clean, test_bug_kind_ticket_with_hand_pasted_cmd_entry_fails_cov003, test_docs_ticket_with_malformed_cmd_entry_fails_cov003, test_transition_refuses_close_when_kind_flipped_after_recording, test_ticket_not_found_propagates_load_error, test_popen_bare_call_still_flags_exec, test_re_compile_is_not_eval, test_c_socket_header_alone_is_not_net, test_openapi_generated_ts_is_not_ffi, test_real_napi_import_still_fires_ffi, _make_frob_repo_root, test_root_none_always_returns_false, test_root_not_frob_repo_returns_false, test_frob_repo_root_with_matching_suffix_returns_true, test_frob_repo_root_with_non_matching_path_returns_false, test_short_path_shorter_than_suffix_returns_false, _init_repo, test_direct_hit, test_class_level_target, test_file_and_package_target, test_one_hop_ripple, test_touched_test_file_self_selects, test_unbound_fallback_package, test_unbound_fallback_suite, test_reversed_directive_never_selects_the_source_symbol, test_unbound_fallback_warn, test_placeholder_ids, test_no_runner_error, test_bad_runner_spec_zero_placeholders, test_bad_runner_spec_two_placeholders, test_missing_frob_toml_is_ok_empty, test_valid_runner_loaded, test_exit_code_is_data, test_pytest_exit_5_no_tests_collected_is_neutral_not_fail, test_package_fallback_with_zero_tests_is_ok_end_to_end, test_spawn_failed_nonexistent_binary, test_spawn_failed_timeout, test_select_and_run_in_linked_worktree, test_parses_node_ids_and_caches_on_content_hash, test_nested_test_runner_cwd_is_collected_and_rerooted, test_missing_nested_runner_dir_degrades_to_empty_not_err, test_cargo_env_ok_when_python311_and_libdir_found, _write_crate, test_module_path_to_symref_inline_and_file_module, test_collect_rust_tests_parses_and_caches, test_collect_rust_tests_no_crates_is_ok_empty, test_collect_rust_tests_skips_lib_less_crate, test_collect_rust_tests_still_errs_on_genuine_compile_error, test_collect_rust_tests_err_when_env_unavailable, _workspace_root, test_virtual_workspace_root_descends_to_members, test_root_package_with_nested_workspace_members, test_plain_single_crate_unchanged, test_unparseable_manifest_keeps_old_behavior_and_warns, test_find_crates_honors_graph_exclude, test_walk_test_files_honors_graph_exclude, test_integration_module_path_to_symref_flat_case, test_find_integration_test_files_lists_and_skips_missing_dir, test_load_natives_parses_entries, test_load_natives_missing_table_is_ok_empty, test_load_natives_missing_field_is_err, test_fingerprint_changes_absent_to_built, test_fingerprint_changes_on_rebuild, test_collection_cache_key_reflects_native_state, test_drop_collection_cache_removes_file, test_drop_collection_cache_unremovable_is_false, test_load_natives_malformed_toml_is_err, test_single_file_extension_fingerprinted, test_walk_test_files_matches_suffix_style_test_files, test_content_key_unreadable_file_is_skipped_not_raised, test_native_artifact_digest_resolvable_no_compiled_artifact, test_native_artifact_digest_unreadable_artifact, test_load_natives_or_empty_degrades_on_malformed_config, test_load_cache_unreadable_json_is_none, test_load_cache_key_mismatch_is_none, test_run_collect_only_spawn_failure_is_err, test_run_collect_only_bad_exit_code_is_err, test_python_runner_cwds_degrades_on_bad_runner_config, test_python_runner_cwds_dedupes_repeated_cwd, test_collect_nested_python_propagates_collect_failure, test_collect_python_tests_outer_collection_failure_is_err, test_collect_python_tests_nested_failure_degrades_with_warning, test_rust_content_key_unreadable_file_is_skipped, test_run_cargo_test_list_integration_failure_propagates, test_fetch_false_with_no_cache_degrades_loudly, test_cached_body_parses_cwe_ids, test_nvd_placeholder_cwe_is_dropped, test_malformed_cached_body_degrades_without_raising, test_finds_node_importing_the_package, test_no_node_imports_the_package, test_dash_normalized_dist_name_resolves_to_underscore_module, test_live_finding_when_obligation_undischarged, test_contained_finding_when_obligation_discharged, test_unmodeled_when_no_node_imports_the_package, test_unverified_when_nvd_lookup_fails, test_non_cve_advisory_yields_no_findings, test_ack_then_sig_edit_yields_stale, test_rename_yields_dangling_candidate_via_body_digest, test_acknowledge_unknown_ref_is_err, test_write_lock_deterministic, test_write_lock_is_atomic, test_missing_file_is_empty_lock, test_malformed_json_is_err, test_forbidden_import_fires, test_forbidden_import_passes_outside_glob, test_forbidden_import_malformed_missing_field, test_pattern_query_matches, test_pattern_bad_query_is_err, test_pattern_missing_query_file_is_err, test_norm_max_diff_lines_fires, test_norm_passes_under_limit, test_norm_malformed_missing_max_lines, test_no_frob_toml_is_ok_empty, _seed_in_progress_ticket, _write_rust_runner_toml, _init_repo, test_stripe_live_key_sec003, test_pem_private_key_header_flagged_sec003, test_anthropic_key_flagged_sec001, test_sec003_waiver_is_inert, test_generic_live_key_adjacent_to_other_content_sec001, test_stripe_test_key_is_low_severity_warn, test_placeholder_xxxx_tail_is_not_flagged, test_literal_fake_word_in_token_is_not_flagged, test_fake_marker_same_line, test_frob_secret_fake_marker_on_line_above, test_placeholder_phrase_your_dash_here_is_not_flagged, test_placeholder_phrase_insert_dash_is_not_flagged, test_placeholder_phrase_does_not_suppress_real_looking_token, test_placeholder_phrase_your_does_not_suppress_high_entropy_token, test_placeholder_phrase_insert_does_not_suppress_high_entropy_token, test_placeholder_phrase_here_does_not_suppress_high_entropy_token, test_digit_free_mixed_case_your_token_still_fires, test_digit_free_insert_alphabet_run_still_fires, test_digit_free_mixed_case_here_tail_still_fires, test_env_file_sec002, test_env_example_is_not_flagged, test_untracked_env_file_is_never_scanned, test_tracked_binary_file_is_skipped_not_crashed, test_embedded_overlapping_match_is_not_double_claimed, test_every_provider_has_a_fixture, test_disjoint_ids_both_kept, test_same_id_newer_state_wins, test_malformed_ours_propagates_as_err, test_malformed_theirs_propagates_as_err, test_dry_run_lands_cleanly_and_leaves_no_trace, test_real_land_lands, test_refuses_on_dirty_main, test_refuses_without_evidence_or_done_report, test_close_fails_after_merge_when_main_dropped_same_id, test_unowned_deletion_aborts_loudly, test_scoped_deletion_is_allowed, test_both_sides_append_merges_cleanly, test_code_directive_rewritten_and_worktree_clean_after_land, test_archived_id_never_resurrected, test_dry_run_wip_commits_uncommitted_changes, test_real_land_wip_commits_uncommitted_changes, test_non_docs_kind_with_cmd_evidence_refused, test_unowned_deletion_aborts_on_real_run, test_real_conflict_outside_tickets_md_aborts, test_draft_id_finalized_on_land, test_unknown_ticket_id_returns_not_found, test_unowned_deletion_real_run_with_actual_merge, test_land_refreshes_stale_sweep_after_unrelated_main_change, test_module_level_call_expression_const_extracted, test_content_hash_changes_on_any_byte_change, test_reformat_preserves_tokens, test_param_rename_changes_sig_only, test_body_edit_changes_body_only, test_docstring_edit_changes_only_doc_text, test_rust_pyo3_export_is_public_without_pub, test_rust_directive_binds_above_proptest_macro_block, test_rust_non_test_macro_does_not_bind, test_rust_directive_binds_above_stacked_attributes, test_rust_directive_binds_above_single_attribute, test_rust_directive_binds_directly_above_keyword_no_attrs, test_rust_directive_binds_below_attributes_workaround_placement, test_rust_directive_binds_above_one_line_rustdoc, test_rust_directive_binds_above_multiline_rustdoc, test_rust_directive_binds_above_zero_line_rustdoc, test_rust_directive_binds_regardless_of_indentation_mismatch, test_unsupported_extension, test_unreadable_path, test_lang_pipeline_integration, test_find_lockfile_uv, test_find_lockfile_none, test_find_lockfile_direct, test_find_lockfile_bad_name, test_parse_uv_lock, test_parse_package_lock_json_v3, test_parse_package_lock_json_v1, test_parse_pnpm_lock, test_parse_cargo_lock, test_unsupported_lockfile, test_malformed_uv_lock, test_no_frob_toml_is_advisory_only, test_no_vet_section_is_advisory_only, test_vet_section_present, test_wrong_typed_scalars_fall_back_to_defaults, test_scan_file_operations_names_registry_entry, test_scan_file_operations_no_language, test_scan_file_operations_bare_compile, test_scan_file_operations_dotted_compile_not_matched, test_scan_file_operations_unreadable_file, test_python_exec_and_net_detected, test_rust_exec_detected, test_kotlin_net_okhttp_detected, test_kotlin_exec_runtime_exec_detected, test_kotlin_client_storage_shared_preferences_detected, test_kotlin_benign_file_has_no_capabilities, test_c_source_exec_detected, test_decode_to_exec_same_function, test_decode_to_exec_absent_when_separate, test_language_for_known_and_unknown_extensions, test_scan_directory_capabilities_aggregates_across_files, test_re_compile_alone_does_not_report_eval, test_bare_compile_call_still_reports_eval, test_genuine_eval_still_detected, test_comment_only_needle_does_not_fire, test_real_code_needle_still_fires_alongside_comment, test_string_literal_needle_still_fires, test_scan_directory_capabilities_excludes_own_module, test_import_as_alias_detected, test_from_import_detected, test_from_import_as_detected_with_correct_kind, test_import_as_alias_operation_names_registry_entry, test_method_shadowing_import_not_detected, test_param_shadowing_import_not_detected, test_local_variable_shadowing_import_not_detected, test_bare_name_call_with_no_import_not_detected, test_direct_call_still_detected_via_resolver, test_attribute_only_env_access_via_alias_detected, test_single_rebind_detected, test_chained_rebind_detected, test_attribute_rebind_detected, test_benign_rebind_not_detected, test_parameter_shadow_still_not_detected, test_dangerous_then_benign_rebind_stays_detected, test_embedded_html_script_string_detected, test_embedded_code_region_below_size_threshold_not_detected, test_embedded_code_declared_even_when_content_opaque_to_needles, test_embedded_code_regions_scanned_via_operations, test_matches_a_known_fingerprint, test_no_match_on_clean_source, test_matches_the_xxe_fingerprint_positive, test_does_not_match_the_xxe_fingerprint_negative, test_no_language_returns_empty, test_unreadable_file_returns_empty, test_language_mismatch_does_not_match, test_matches_tls_verify_false_python, test_no_match_on_verified_tls_python, test_matches_tls_reject_unauthorized_false_node, test_no_match_on_reject_unauthorized_true_node, test_matches_tls_danger_accept_invalid_certs_rust, test_no_match_on_default_reqwest_builder_rust, test_self_pattern_exclusion_survives_a_foreign_install_copy, test_self_pattern_exclusion_does_not_match_unrelated_same_name_file, test_self_pattern_exclusion_does_not_fire_when_vetting_a_dependency, test_scan_directory_fingerprints_aggregates_across_files, test_scan_directory_fingerprints_excludes_the_catalog_itself, test_scan_directory_obfuscation_finds_signal_in_one_file, test_store_and_retrieve_latest, test_missing_cache_returns_none, test_python_setup_py_cmdclass_flagged, test_python_pth_file_flagged, test_rust_build_rs_capability_flagged, test_scan_tree_lockfile_arg, test_scan_tree_unsupp_err, test_run_unsupp_nonzero, test_scan_tree_flags_undeclared_capability, test_scan_tree_surfaces_a_cve_fingerprint_finding, test_finds_postinstall_script, test_no_node_modules_returns_empty, test_fetch_publish_date_degrades_on_network_failure, test_locate_pypi_source_from_venv, test_locate_pypi_source_missing_returns_none, test_locate_npm_source_from_node_modules, test_locate_npm_source_missing_returns_none, test_locate_source_dispatches_by_ecosystem, test_walk_python_imports_collects_absolute_imports_only, test_walk_python_imports_skips_unparseable_files, test_resolve_import_registry_match, test_resolve_import_registry_match_via_pypi_name_override, test_resolve_import_no_capability_match, test_resolve_import_vetted_via_local_source_scan_and_cache, test_resolve_import_unknown_when_unresolvable, test_closed_world_accounting_source_unavailable, test_closed_world_accounting_full_pass, test_closed_world_accounting_closed_when_no_unknowns, test_round_trip_load, test_body_preserved_verbatim, test_malformed_frontmatter_is_err, test_unknown_frontmatter_key_is_err, test_duplicate_id_is_err, test_allocates_sequential_id, test_first_ticket_gets_0001, test_add_evidence_appends_and_round_trips, test_add_evidence_rejects_malformed_entry_before_write, test_new_ticket_validates_evidence, test_transition_queued_to_planned_unit, test_planned_to_in_progress, test_in_progress_to_blocked, test_blocked_to_in_progress, test_in_progress_to_queued_yield, test_in_progress_to_dropped, test_in_progress_to_done_with_evidence_and_report, test_done_without_evidence_errs, test_done_without_report_section_errs, test_start_with_open_blocker_errs, test_blocker_done_unblocks, test_blocker_dropped_unblocks, test_unknown_ticket_not_found, test_ordering_by_created_then_id, test_blocked_excluded, test_planned_included, test_in_progress_excluded, test_appends_creates_section, test_appends_existing_section_preserves_rest, test_unknown_ticket_not_found, test_file_source_copies_and_records_sha256, test_index_increments, test_unknown_ticket_not_found, test_resolvable_ids_appended, test_parametrized_bare_name_matches, test_unresolvable_id_rejected, test_mixed_batch_rejected_wholesale, test_dedupes_against_existing_evidence, test_unknown_ticket_not_found, test_moves_done_and_dropped_only, test_idempotent_second_run_moves_nothing, test_nothing_to_archive_is_zero, test_load_queue_merges_active_and_archive, test_blocked_by_archived_ticket_resolves_closed, test_new_ticket_id_continues_past_archived_max, test_new_ticket_fresh_repo_no_archive_file, test_new_ticket_corrupt_archive_fails_loudly, test_tickets_queue_workflow_integration, test_new_ticket_normalizes_comma_joined_scope, test_round_trips, test_merges_with_prior_stamp, test_missing_stamp_is_none, test_non_python_target_returns_none, test_malformed_ref_returns_none, test_unimportable_module_returns_none, test_introspects_a_real_function, test_strips_self_param_on_method, test_nested_module_path_derives_dotted_name, test_unresolvable_qualname_returns_none, test_non_callable_attribute_returns_none, test_invariant_anchor_in_real_source_is_obligated, _init_repo, test_own_file_not_scanned, test_reformat_identical_digests, test_param_rename_moves_sig_only, test_body_edit_changes_body_only, test_docstring_edit_changes_doc_only, test_digest_sig_body_doc_are_independent_facets, test_hash_comment_directive, test_slash_slash_directive, test_block_comment_directive, test_binds_to_enclosing_symbol, test_binds_to_following_symbol, test_binds_to_nested_method_not_enclosing_class, test_binds_three_stacked_directives_to_def, test_binds_five_stacked_directives_to_def, test_directive_binds_past_trailing_comment_on_def_line, test_stacked_directives_bind_past_trailing_comment_on_def_line, test_directive_does_not_chain_upward_through_prior_trailing_comment, test_directive_separated_from_def_by_non_directive_comment, test_directive_separated_from_def_by_blank_line, test_bare_file_when_no_binding, test_tests_verb_attrs, test_tests_verb_default_kind, test_tests_verb_invalid_kind_is_malformed, test_unknown_verb_is_malformed, test_missing_target_is_malformed, test_waive_without_reason_is_malformed, test_bad_attr_syntax_is_malformed, test_second_build_is_all_cache_hits, test_touching_one_file_reparses_only_it, test_cache_hit_build_reports_real_edge_count, test_glob_excludes_matching_files, test_no_config_excludes_nothing_extra, test_nested_git_worktree_pruned_without_config, test_exact_match, test_suffix_unique_match, test_ambiguous, test_unknown, test_edges_from_and_to, test_cache_stale_after_edit, test_cache_corrupt_on_garbage, test_cache_corrupt_when_missing, test_load_graph_success_returns_snapshot, test_deleted_cache_is_rebuildable_from_source, test_set_root_and_get_root_roundtrip, test_store_and_load_file_data_roundtrip, test_connect_readonly_rejects_writes_no_lock_contention, test_connect_on_current_schema_does_not_block_on_a_held_write_lock, test_graph_build_lock_drift_integration, test_is_generated_source_detects_repo_convention_header, test_is_generated_source_detects_do_not_edit_and_at_markers, test_is_generated_source_false_for_hand_authored_file, test_is_generated_source_false_for_missing_file, _init_hot_cold_workload, test_main_cli_dispatches, test_version_flag_prints_version_and_exits_zero, test_app_runner_map, test_map_project, test_outline_file, test_xref_symbol, test_cycle_cli, test_gitlog, test_testing_collect, test_policy_load, test_serve_tools, test_deploy_generate_writes_and_checks, test_clean_model_exits_zero, test_undischarged_capability_exits_nonzero_with_named_gap, test_file_arg_fails, test_no_design_dir_is_a_noop, test_new_ticket_no_dot_frob_lands_in_worktree, test_ticket_new_with_dot_frob_in_worktree_only, test_ticket_show_reads_worktrees_own_ledger, test_ticket_start_prework_written_under_worktree, test_non_install_command_fast_exits_zero, test_empty_hook_command_fast_exits_zero, test_typosquat_blocks_without_network, test_renders_matrix_for_default_view, test_unknown_view_exits_nonzero, test_no_design_dir_is_a_noop, test_sys_audit_fails_loud_when_strata_present, test_check_fails_loud_with_sys004_when_strata_present, test_check_unaffected_when_no_strata_files, test_all_registered_types_render_without_error, test_dry_run_prints_tree_without_writing, test_dry_run_names_apply_flag_in_label, test_apply_writes_ticket_tree, test_second_apply_is_a_noop, test_threat_pre_discharge_count_never_reads_as_contradicting_output, test_dropped_ticket_is_not_recreated, test_sys_gate_zero_violations, _init_repo, test_dry_run_reports_clean, test_iter_functions_py_yields_qualified_names, test_enclosing_class_py_none_for_top_level_function, test_enclosing_class_py_finds_class_for_method, test_collect_locals_py_covers_every_binding_shape, test_collect_locals_py_with_tuple_target, test_collect_locals_py_method_includes_typed_default_param, test_collect_locals_py_empty_for_body_with_no_bindings, test_serialize_py_body_renames_locals_and_normalizes_literals, _init_frob_repo, test_render_project_writes_expected_files, test_render_project_existing_output_without_force_is_err, test_render_project_force_overwrites_existing_output, test_render_project_all_registered_types_succeed, test_resolve_manifest_paths_bad_output_expression_is_render_failed, test_write_manifest_entries_missing_template_is_template_not_found, test_render_project_propagates_resolve_failure, test_bytes_content_write_mode, test_tickets_dir_is_repo_relative, test_ledger_path_is_tickets_md_at_root, test_attachments_dir_nests_under_ticket_id, test_fresh_repo_defaults_to_single, test_ledger_present_is_single, test_only_legacy_dir_files_is_dir, test_round_trip, test_malformed_file_is_err, test_write_then_load_single_mode, test_load_all_empty_repo_is_empty_dict, test_moves_legacy_files_into_ledger, test_no_legacy_files_is_zero, test_archive_path_at_root, test_load_archive_missing_file_is_empty, test_write_then_load_archive_round_trips, test_archive_format_matches_ledger_marker, test_writes_text_content, test_writes_bytes_content, test_no_leftover_temp_file, _init_repo, test_git_log, test_parse_ticket_file_no_frontmatter_block, test_parse_ticket_file_bad_yaml, test_parse_ticket_file_roundtrips_valid, test_write_ticket_single_mode_existing_load_error_propagates, test_write_all_dir_mode_prunes_stale_files, test_migrate_to_ledger_empty_is_noop, test_migrate_to_ledger_malformed_file_fails_closed, test_migrate_to_ledger_moves_dir_files_into_ledger, test_unknown_command_exits_1, test_build_success_logs_stats, test_query_requires_ref, test_query_unresolvable_ref_exits_1, test_query_text_mode_prints_record, test_query_json_mode_prints_json, test_why_requires_ref, test_why_unresolvable_ref_exits_1, test_why_text_mode_not_acked, test_why_json_mode_prints_json, test_query_with_edges_renders_both_directions, test_unknown_command_exits_1, test_profile_requires_argv_or_tests, test_profile_and_heat_round_trip, test_heat_json_mode, test_heat_top_and_smells, test_heat_annotate_writes_gutters, test_heat_no_artifact_exits_1, test_heat_annotate_missing_file_exits_1, test_profile_failure_propagates_workload_exit_code, test_heat_annotate_outside_root_uses_absolute_path, test_nonexistent_path_exits_1, test_comment_inside_a_block_binds_as_enclosing, test_parse_failure_returns_parse_failed, test_graph_build_skips_quietly, test_map_file_node_degrades_without_raising, test_xref_search_does_not_raise, test_unknown_command_exits_1, test_missing_title_or_kind_exits_1, test_no_tickets_logs_message, test_list_json_mode, test_list_filters_by_state, test_list_text_mode_prints_ticket_line, _write_malformed_ledger, test_list_load_error_exits_1, test_show_load_error_exits_1, test_doable_load_error_exits_1, test_missing_id_exits_1, test_unknown_id_exits_1, test_show_found_json_mode, test_show_found_text_mode, test_nothing_doable, test_doable_json_mode, test_doable_text_mode, test_no_legacy_files, test_migrates_legacy_dir_ticket, test_dry_run_without_old_new_exits_1, test_whole_ledger_already_contiguous, test_one_missing_new_id_exits_1, test_renumber_one_success, test_missing_id_exits_1, test_missing_worktree_exits_1, test_missing_id_exits_1, test_plan_success, test_missing_id_exits_1, test_unknown_id_exits_1, test_start_auto_plans_queued_ticket, test_start_already_in_progress_exits_1, test_missing_id_exits_1, test_not_in_progress_exits_1, test_missing_id_exits_1, test_attach_from_path_success, test_missing_args_exits_1, test_block_success, test_missing_id_exits_1, test_close_queued_gives_start_hint, test_close_missing_evidence_gives_hint, test_missing_args_exits_1, test_unknown_id_exits_1, test_fail_records_attempt, test_missing_args_exits_1, test_evidence_cmd_applied_for_docs_ticket, test_evidence_cmd_failure_logs_error, test_nothing_to_archive, test_archives_done_ticket, test_unknown_command_exits_1, test_no_design_models, test_dry_run_prints_plan, test_apply_writes_tickets, test_file_arg_fails, test_malformed_design_file_exits_1, test_custom_design_dir_from_frob_toml, test_unreadable_frob_toml_falls_back_to_default, test_unchanged_model_second_run_no_new_tickets, test_no_design_models, test_renders_matrix, test_malformed_design_file_exits_1, test_unknown_view_exits_1, test_bad_format_exits_1, test_directory_path_exits_1, test_missing_path_exits_1, test_parse_failure_exits_1, test_default_design_path, test_no_design_models, test_clean_model_passes, test_malformed_design_file_exits_1, test_waived_gap_still_proves_clean, test_gap_model_exits_1, test_file_arg_fails, test_all_stages_skipped_returns_empty_result_for_root, test_all_stages_skipped_returns_empty_result, test_all_stages_skipped_returns_empty_result, test_all_stages_skipped_returns_empty_result, test_cargo_toml_is_rust, test_cmakelists_is_cpp, test_pyproject_is_python, test_package_json_and_tsconfig_is_typescript, test_no_sentinel_is_unknown, test_malformed_tickets_md_is_hard_error_not_silent_skip, test_no_baseline_falls_back_to_full_set_with_warning, test_stale_baseline_falls_back_to_full_set_with_warning, test_warn_only_gate_summary_splits_errors_and_warnings, test_check_run_check_arch_integration, test_run_check_calls_build_graph_exactly_once, test_newest_mtime_absent_directory_is_none, test_stale_natives_degrades_on_malformed_config, test_merges_ids, test_no_dir_empty, test_bad_file_reported, test_one_bad_file_does_not_hide_a_good_one, test_excluded_no_ids, _write_design, _write_design, _write_design, test_long_reason_continues_across_lines, test_folded_directive_reports_first_physical_lineno, test_join_uses_empty_string_not_space, test_three_line_continuation, test_normal_single_line_directive_unchanged, test_dangling_backslash_on_last_comment_line_is_literal, test_crlf_before_trailing_backslash_is_safe, test_verb_agnostic_multiline_tests_directive, test_unrelated_directives_on_consecutive_lines_do_not_fold, test_secret_fake_is_silently_skipped, test_unreserved_unknown_verb_still_reports_malformed, test_waive_with_trailing_noqa_parses, test_tests_with_trailing_bare_noqa_binds, test_hash_inside_quoted_value_is_preserved, test_doc_before_two_ticket_lines_still_binds_via_generic_walker, _register_query_tools, _register_scope_tool, run_stdio, check_native_staleness_or_exit, _abort_merge, _run_stamp_coverage, _migrate, _report_land_result, _run_sweep, _archive, _run_fuzz, _refresh_collection, _stamp, _check, _require_export_design_path
  Consider a shared protocol or base class
tests/test_gates.py  suggestion  abstraction-opportunity
  94 functions share signature `(Path, pytest.MonkeyPatch) -> None`: test_unreadable_file_is_malformed, test_no_design_dir_never_imports_frob_strata, test_design_dir_degrades_with_typed_error_on_native_extension_missing, test_run_argv_failure_surfaces_as_not_a_repo, test_diff_command_failure_propagates, test_untracked_listing_failure_propagates, test_write_failure_propagates, test_path_resolve_oserror_returns_false, test_network_failure_degrades_loudly, test_network_success_populates_cache, test_expired_cache_entry_triggers_a_fresh_fetch, test_resolvable_evidence_recorded_on_new_ticket, test_unresolvable_evidence_does_not_abort_ticket_creation, test_dedupes_against_already_recorded_evidence, test_resolvable_evidence_recorded_then_closed, test_unresolvable_evidence_blocks_close_entirely, test_dedupes_against_ids_already_on_ticket, test_rust_node_id_from_fake_cargo_collect_cache_resolves, test_no_rust_runner_declared_never_collects_rust, test_rust_collection_failure_degrades_to_python_only, test_spawn_error_yields_no_tracked_files, test_nonzero_exit_yields_no_tracked_files, test_main_dirty_check_git_failure, test_main_branch_lookup_failure, test_wip_commit_status_check_failure, test_merge_command_failure, test_unowned_deletions_diff_failure_after_merge, test_squash_command_failure, test_final_commit_failure, test_post_merge_commit_failure, test_finalize_draft_failure, test_worktree_branch_lookup_failure_after_close, test_sweep_refresh_failure_does_not_block_landing, test_fresh_package_blocked, test_old_package_ok, test_network_failure_degrades_to_unverified, test_scan_tree_detects_capabilities_from_node_modules, test_slow_package_returns_within_timeout_not_task_duration, test_run_osv_scan_none_when_binary_absent, test_locate_cargo_source_missing_registry_returns_none, test_fingerprint_bump_rebuilds, test_walk_source_files_prunes_before_descent, test_load_graph_never_built_root_is_corrupt, test_load_graph_get_root_query_error_is_corrupt, test_load_graph_connect_readonly_failure_is_corrupt, test_connect_error_is_propagated_without_writing, test_atomic_write_failure_propagates, test_source_unlink_failure_is_warned_not_fatal, test_nested_unlink_failure_after_write_error_is_swallowed, test_atomic_write_oserror_returns_write_failed, test_build_failure_exits_1, test_query_snapshot_unavailable_exits_1, test_why_lock_load_failure_exits_1, test_why_snapshot_unavailable_exits_1, test_why_acked_stale_dangling_render_lines, test_profile_command_error_exits_1, test_profile_tests_flag_builds_pytest_argv, test_heat_snapshot_build_failure_exits_1, test_heat_annotate_unreadable_file_exits_1, test_stamp_coverage_mode_calls_stamp_and_returns, test_stamp_coverage_failure_exits_1, test_stamp_baseline_mode_calls_stamp_and_returns, test_stamp_baseline_gate_error_exits_1, test_auto_detected_python_stage_dispatches_and_passes, test_json_mode_prints_json_and_errors_exit_1, test_pinned_type_warns_polyglot_and_skips_others, test_pinned_cpp_dispatches_run_check_cpp, test_pinned_rust_dispatches_run_check_rust, test_pinned_typescript_dispatches_run_check_ts, test_frob_toml_defaults_applied, test_frob_toml_unreadable_warns_and_continues, test_deploy_stages_appended_when_deploy_dir_present, test_verbose_levels_do_not_crash, test_renumber_one_dry_run_prints_files, test_land_failure_exits_1, test_land_dry_run_success, test_land_success_prints_files, test_transition_to_in_progress_failure_exits_1, test_no_clipboard_image_skips, test_declined_answer_skips_attach, test_accepted_answer_attaches, test_no_path_non_tty_exits_1, test_close_with_bad_evidence_ids_exits_1_without_closing, test_evidence_ids_applied, test_apply_new_ticket_failure_exits_1, test_reports_native_grammar_ahead_of_native, test_fresh_native_reports_nothing, test_unbuilt_native_is_not_reported_as_stale, test_no_matching_source_dir_is_not_reported, test_returns_none_when_not_stale, test_newest_mtime_skips_unstatable_file_and_keeps_max, test_artifact_mtime_no_compiled_artifact_is_none, test_artifact_mtime_unstatable_artifact_is_none, test_stale_natives_skips_empty_source_dir
  Consider a shared protocol or base class
tests/test_gates.py  suggestion  abstraction-opportunity
  9 functions share signature `(Path, pytest.LogCaptureFixture) -> None`: test_perf_gate_silences_unscannable_files, test_untracked_directory_is_skipped_not_read_as_file, test_close_on_queued_hint_names_start, test_missing_evidence_hint_names_tickets_md, test_hints_at_sweep_and_exits_nonzero, test_real_land_no_warning_when_native_fresh, test_large_file_logs_warning, test_fresh_build_names_malformed_file, test_cache_hit_rebuild_still_names_malformed_file
  Consider a shared protocol or base class
tests/test_tickets_cmd_evidence.py  suggestion  abstraction-opportunity
  33 functions share signature `(pytest.MonkeyPatch) -> None`: test_oserror_on_launch_is_evidence_cmd_failed, _clear_env, _no_backends, test_wl_paste_selected_when_wayland, test_xclip_selected_when_x11, test_wayland_preferred_over_x11, test_wsl_detection_via_proc_version, test_no_backend_lists_probes_in_message, test_no_image, test_backend_failed_on_nonzero_exit, test_has_image_false_when_no_backend, test_has_image_true_when_wl_paste_lists_png, test_has_image_true_when_xclip_lists_png_target, test_xclip_probe_returns_false_when_no_png_target, test_xclip_no_image_data_is_err, test_xclip_backend_failed_on_nonzero_exit, test_darwin_pngpaste_selected_and_reads_image, test_pngpaste_backend_failed_and_no_image, test_pngpaste_has_image_true_and_false, test_wsl_backend_requires_powershell_binary, test_wsl_has_image_true_and_false, test_wsl_save_reports_no_image_on_exit_code_2, test_wsl_save_backend_failed_on_other_nonzero_exit, test_wsl_save_backend_failed_when_output_file_missing, test_wsl_wslpath_failure_is_backend_failed, test_probe_report_lists_all_four_backends, test_is_wsl_reads_proc_version_case_insensitively, test_is_wsl_false_when_proc_version_missing, test_is_available_reflects_path_lookup, test_no_generator_target_short_circuits_without_hypothesis, test_digests_map_is_stamped_onto_matching_ref, test_hypothesis_unavailable_returns_empty_and_logs, test_artifact_mtime_find_spec_error_is_none
  Consider a shared protocol or base class
tests/test_testing.py  suggestion  abstraction-opportunity
  3 functions share signature `(Path, dict[str, str]) -> None`: _write_files, _run_generate_check, _write_generated_files
  Consider a shared protocol or base class
tests/test_testing.py  suggestion  abstraction-opportunity
  16 functions share signature `(str)`: _boom, _boom, _symbol, _symbol, _module, _elaborate, _elaborate, _boom, _evaluate, _elaborate, _module, _elaborate, _elaborate, _elaborate, _model, __getattr__
  Consider a shared protocol or base class
tests/test_mutate.py  suggestion  abstraction-opportunity
  3 functions share signature `(str, int) -> str`: _mutate_single, _excerpt, _excerpt
  Consider a shared protocol or base class
tests/test_ticket_land.py  suggestion  abstraction-opportunity
  3 functions share signature `(list[str], Path) -> subprocess.CompletedProcess`: _run, _git, _git
  Consider a shared protocol or base class
tests/test_fuzz.py  suggestion  abstraction-opportunity
  9 functions share signature `(str) -> None`: __init__, commit, _send, commit, __init__, add_node, _strongconnect, _pop_component, _log_evidence_result
  Consider a shared protocol or base class
tests/test_graph.py  suggestion  abstraction-opportunity
  3 functions share signature `(Path, str, str)`: _parse, _load_ticket_or_exit, _apply_cmd_evidence
  Consider a shared protocol or base class
tests/test_arch_gate.py  suggestion  abstraction-opportunity
  34 functions share signature `(str) -> str`: _flat_long_source, _new_ticket_id, _slugify, _symref_to_nodeid, _interface_package, _snake, _consumer_leaf, _strip_inline_code_spans, _to_node_id, _to_rust_filter, _edge_symref_path, _cache_key, _best_effort_version, _module_name, _normalize_py_name, _first_doc_line, _may_kind, _pii_protection_claim_id, _frame_target_base, _code_only, collapse_ws, strip_comment_delims, _normalize, _unit_name, _unit_file_path, _unit_enable_start_block, remap, slugify, _sha16, _ref_path, _waiver_hint, slugify, _short_name, _close_failure_hint
  Consider a shared protocol or base class
tests/test_arch_gate.py  suggestion  abstraction-opportunity
  6 functions share signature `(str, str) -> str`: _complex_long_source, redact, _join_candidate, _marker, _join_dotted, _discharge_claim_id
  Consider a shared protocol or base class
tests/system/test_cli_sys_audit.py  suggestion  abstraction-opportunity
  10 functions share signature `(str, Path) -> None`: _git, _git, _git, _git, _git, _git, _git, _git, _git, _git
  Consider a shared protocol or base class
tests/system/test_cli_sys_audit.py  suggestion  abstraction-opportunity
  7 functions share signature `(Path, str) -> Path`: _init_repo, _init_design_repo, _write_design_repo, _init_design_repo, _prework_path, _scope_pattern_scan_path, attachments_dir
  Consider a shared protocol or base class
tests/unit/test_check_tool_unavailable.py  suggestion  abstraction-opportunity
  8 functions share signature `(pytest.MonkeyPatch, Path) -> None`: test_run_ruff_missing_binary_returns_failing_results, test_ruff_format_result_missing_binary_returns_failing_result, test_run_ty_missing_binary_returns_failing_result, test_run_cargo_missing_binary_returns_failing_result, test_run_cargo_fmt_check_missing_binary_returns_failing_result, test_run_cargo_test_missing_binary_returns_failing_result, test_run_tsc_missing_npx_returns_failing_result, test_as_text_shows_unavailable_tool_line
  Consider a shared protocol or base class
tests/unit/test_runtime_deps.py  suggestion  abstraction-opportunity
  3 functions share signature `(Path) -> set[str]`: _top_level_imports, _embedded_capabilities, _conflicted_files
  Consider a shared protocol or base class
tests/unit/test_research_assets.py  suggestion  abstraction-opportunity
  4 functions share signature `(str) -> set[str]`: _heading_slugs, _extract_construct_keywords, _extract_clause_keywords, neighbors
  Consider a shared protocol or base class
tests/unit/test_claims_and_store_batch6.py  suggestion  abstraction-opportunity
  9 functions share signature `(str, str) -> Node`: _node, _node, _node, _node, _node, _node, _node, _node, _node
  Consider a shared protocol or base class
tests/unit/test_claims_and_store_batch6.py  suggestion  abstraction-opportunity
  8 functions share signature `(str, str, str) -> Flow`: _flow, _flow, _flow, _flow, _flow, _flow, _flow, _flow
  Consider a shared protocol or base class
tests/unit/strata/test_litmus_payments.py  suggestion  abstraction-opportunity
  3 functions share signature `(bool) -> KernelModel`: _payments_model, _coppa_model, _erasure_model
  Consider a shared protocol or base class
tests/unit/strata/test_litmus_payments.py  suggestion  abstraction-opportunity
  5 functions share signature `(KernelModel) -> dict[str, ClaimResult]`: _results, _results, _results, _results, _results
  Consider a shared protocol or base class
tests/unit/strata/test_crash.py  suggestion  abstraction-opportunity
  4 functions share signature `(float) -> Quantity`: _seconds, _seconds, _seconds, _rate
  Consider a shared protocol or base class
tests/unit/strata/test_litmus_surface.py  suggestion  abstraction-opportunity
  11 functions share signature `(str) -> KernelModel`: _load_model, _load_model, _load_model, _load_model, _load_model, _load_model, _load_model, _load_model, _load_litmus_model, _load_model, _load_model
  Consider a shared protocol or base class
src/frob/excludes.py  suggestion  abstraction-opportunity
  3 functions share signature `(Path) -> tuple[str, ...]`: load_exclude_globs, _tracked_python_files, _tracked_files
  Consider a shared protocol or base class
src/frob/excludes.py  suggestion  abstraction-opportunity
  3 functions share signature `(str, tuple[str, ...]) -> bool`: is_excluded, _scenario_has_bound_claim, _in_scope
  Consider a shared protocol or base class
src/frob/excludes.py  suggestion  abstraction-opportunity
  32 functions share signature `(str) -> bool`: is_skipped_dir, is_test_file, _is_allowlisted_env_var, _looks_low_entropy, _looks_fake, _is_env_file, _is_test_path, _is_native_test_src, _is_native_test_symref, _looks_like_test_symbol, wanted, _body_reaches_decode_and_exec, invisible_text_signal, hex_identifier_ratio_signal, visit, _gap_rule_in_scope, _mode_owner_writable, _mode_has_setuid, _is_major_version, _is_skip_dir, _is_fixture_data_file, _is_init_file, _hit, _is_allowlisted, assert_not_installed, _is_redirect_op, _has_done_report, is_cmd_evidence, is_draft_id, _has_done_report, _is_test_or_private_path, _is_endpoint
  Consider a shared protocol or base class
src/frob/excludes.py  suggestion  abstraction-opportunity
  3 functions share signature `(Path, Path) -> bool`: _is_nested_worktree, _is_hidden, _is_self_path
  Consider a shared protocol or base class
src/frob/logging/formatter.py  suggestion  abstraction-opportunity
  3 functions share signature `(bool) -> None`: __init__, walk, _print_items
  Consider a shared protocol or base class
src/frob/gates/_pii_structural.py  suggestion  abstraction-opportunity
  3 functions share signature `(str, int, str) -> Violation`: _sec110_violation, _doc003_violation, _docanchor_violation
  Consider a shared protocol or base class
src/frob/gates/_pii_structural.py  suggestion  abstraction-opportunity
  4 functions share signature `(Path) -> tuple[Violation, ...]`: pii_structural_gate, secrets_gate, arch_gate, _tick001_duplicate_ids
  Consider a shared protocol or base class
src/frob/gates/_coverage.py  suggestion  abstraction-opportunity
  8 functions share signature `(Path) -> str | None`: _sha_of, _sha_of, _current_version, language_for, _read_scannable_text, _run_osv_scanner, stale_native_warning, _content_hash
  Consider a shared protocol or base class
src/frob/gates/__init__.py  suggestion  abstraction-opportunity
  4 functions share signature `(str, frozenset[str]) -> bool`: _node_id_collected, _macro_file_collected, assert_healthy, _matches_collected
  Consider a shared protocol or base class
src/frob/gates/__init__.py  suggestion  abstraction-opportunity
  9 functions share signature `(str) -> str | None`: _macro_symbol_file, _real_symbol_for_scope_pattern, extension_language, _pii_category, _mode_digits, language_for_extension, _tag_from_refs, _summary_marker, _module_name
  Consider a shared protocol or base class
src/frob/gates/__init__.py  suggestion  abstraction-opportunity
  3 functions share signature `(str, str) -> bool`: _glob_prefix_match, _needle_matches_resolved, satisfies
  Consider a shared protocol or base class
src/frob/gates/__init__.py  suggestion  abstraction-opportunity
  3 functions share signature `(GraphSnapshot) -> tuple[Violation, ...]`: _waive001_violations, _test006, _test010_violations
  Consider a shared protocol or base class
src/frob/gates/__init__.py  suggestion  abstraction-opportunity
  3 functions share signature `(GraphSnapshot) -> list[Violation]`: _drift001, _sys001, _sys002
  Consider a shared protocol or base class
src/frob/gates/__init__.py  suggestion  abstraction-opportunity
  5 functions share signature `(GraphSnapshot) -> set[str]`: _documented_srcs, _invariant_anchors, _linked_from_edges, _anchored_decisions, _edge_endpoints
  Consider a shared protocol or base class
src/frob/gates/__init__.py  suggestion  abstraction-opportunity
  10 functions share signature `(Path, GraphSnapshot) -> tuple[Violation, ...]`: _cov001, decisions_gate, sys_gate, dup_gate, release_gate, fuzz_gate, _fuzz_gate_violations, doclink_gate, docanchor_gate, perf_gate
  Consider a shared protocol or base class
src/frob/gates/__init__.py  suggestion  abstraction-opportunity
  4 functions share signature `(GraphSnapshot, CollectedTests, TestPolicy) -> tuple[Violation, ...]`: _test001_002, _test003, _test009, _test007_pairs
  Consider a shared protocol or base class
src/frob/gates/__init__.py  suggestion  abstraction-opportunity
  3 functions share signature `(GraphSnapshot) -> list[str]`: _public_packages, _design_files, _perf_gate_candidate_paths
  Consider a shared protocol or base class
src/frob/gates/__init__.py  suggestion  abstraction-opportunity
  15 functions share signature `(Path) -> str`: _design_dir, _content_key, _rust_content_key, detect_project_type, _read_text_or_empty, _display_path, _display_root, _design_dir, _read_ledger_text_or_empty, _default_branch, store_mode, _design_dir, _scope_digest_for_ticket, _version, _design_dir
  Consider a shared protocol or base class
src/frob/gates/__init__.py  suggestion  abstraction-opportunity
  3 functions share signature `(Path) -> list[Violation]`: _sys003_one_model, _sys003, _doc003
  Consider a shared protocol or base class
src/frob/gates/__init__.py  suggestion  abstraction-opportunity
  3 functions share signature `(Path, str) -> bool`: _changelog_mentions, _has_tree_sitter_grammar, is_generated_source
  Consider a shared protocol or base class
src/frob/testing/_collect.py  suggestion  abstraction-opportunity
  9 functions share signature `(Path) -> list[Path]`: _walk_test_files, _find_test_files, _find_crates, _find_integration_test_files, _sorted_py_files, _sorted_capability_files, _collect_files, _tracked_files, _dir_glob
  Consider a shared protocol or base class
src/frob/testing/_collect.py  suggestion  abstraction-opportunity
  6 functions share signature `(Path) -> bool`: _is_compiled_artifact, drop_collection_cache, _has_bind_markers, decode_to_exec_signal, _is_test_path, on_default_branch
  Consider a shared protocol or base class
src/frob/testing/_collect.py  suggestion  abstraction-opportunity
  4 functions share signature `(Path) -> list[str]`: _python_runner_cwds, _repo_files_excluding_skip_dirs, _top_level_dirs, _detected_types
  Consider a shared protocol or base class
src/frob/testing/_collect.py  suggestion  abstraction-opportunity
  5 functions share signature `(str) -> list[str]`: _parse_cargo_list, _missing_exports, _iter_string_literals, _tokenize_line, _render_query_lines
  Consider a shared protocol or base class
src/frob/xref/__init__.py  suggestion  abstraction-opportunity
  5 functions share signature `(bool) -> str`: as_text, as_text, _header_line, as_text, as_text
  Consider a shared protocol or base class
src/frob/check/_python.py  suggestion  abstraction-opportunity
  9 functions share signature `(Path) -> ToolResult`: _ruff_format_result, _run_ty, _run_cycle, _run_dup, _run_arch, _run_tsc, _run_eslint, _run_prettier, _run_vitest
  Consider a shared protocol or base class
src/frob/check/_python.py  suggestion  abstraction-opportunity
  6 functions share signature `(Path) -> ToolResult | None`: _run_bind, _run_clang_format, _run_cargo_fmt_check, _run_cargo_valgrind, _deploy_drift_result, _deploy_conformance_result
  Consider a shared protocol or base class
src/frob/check/_python.py  suggestion  abstraction-opportunity
  3 functions share signature `(Path, Path) -> ToolResult | None`: _exports_for_package, _cmake_configure, _run_clang_tidy_cmake
  Consider a shared protocol or base class
src/frob/check/_ts.py  suggestion  abstraction-opportunity
  4 functions share signature `(str, str) -> ToolResult`: _missing_tool_result, parse_junit_xml, tool_unavailable_result, _skip_note_result
  Consider a shared protocol or base class
src/frob/check/_ts.py  suggestion  abstraction-opportunity
  5 functions share signature `(str) -> list`: _parse_vitest_report, _edges_by_kind_value, _acked_for, _stale_for, _dangling_for
  Consider a shared protocol or base class
src/frob/check/_native.py  suggestion  abstraction-opportunity
  3 functions share signature `(Path, tuple[str, ...]) -> list[Path]`: _collect_sources, _walk_source_files, _walk_doc_files
  Consider a shared protocol or base class
src/frob/perf/_heat.py  suggestion  abstraction-opportunity
  3 functions share signature `(Path, str) -> str | None`: _relativize, _cache_get, _cache_get
  Consider a shared protocol or base class
src/frob/perf/_rules.py  suggestion  abstraction-opportunity
  4 functions share signature `(tuple[str, ...], tuple[int, ...]) -> bool`: _perf001_python, _perf002_python, _perf003, _perf004_python
  Consider a shared protocol or base class
src/frob/perf/_rules.py  suggestion  abstraction-opportunity
  3 functions share signature `(tuple[str, ...], tuple[int, ...], str) -> bool`: _method_call_in_loop, _perf001_best_effort, _perf002_best_effort
  Consider a shared protocol or base class
src/frob/vet/_ecosystem.py  suggestion  abstraction-opportunity
  5 functions share signature `(Dependency, Path, str) -> Violation | None`: _setup_py_violation, _pth_violation, _pickle_violation, _build_rs_violation, _proc_macro_violation
  Consider a shared protocol or base class
src/frob/vet/_ecosystem.py  suggestion  abstraction-opportunity
  3 functions share signature `(Dependency, Path, str) -> list[Violation]`: python_rules, rust_rules, _ecosystem_rules
  Consider a shared protocol or base class
src/frob/vet/_hook.py  suggestion  abstraction-opportunity
  3 functions share signature `(str) -> tuple[str, str]`: _strip_pypi_version, _strip_npm_version, _strip_cargo_version
  Consider a shared protocol or base class
src/frob/vet/_lockfile.py  suggestion  abstraction-opportunity
  3 functions share signature `(Path) -> Result[tuple[Dependency, ...], VetError]`: parse_lockfile, _parse_package_lock_json, _parse_pnpm_lock
  Consider a shared protocol or base class
src/frob/vet/_capability.py  suggestion  abstraction-opportunity
  3 functions share signature `(set[str]) -> None`: _collect_target_names, _collect_param_name, _prune_stale_cache
  Consider a shared protocol or base class
src/frob/vet/_capability.py  suggestion  abstraction-opportunity
  3 functions share signature `(dict[str, str], dict[int, frozenset[str]], dict[int, dict[str, str]] | None) -> str | None`: _resolve_py_expr, _resolve_py_identifier, _resolve_py_attribute
  Consider a shared protocol or base class
src/frob/vet/_capability.py  suggestion  abstraction-opportunity
  4 functions share signature `(Path) -> frozenset[str]`: scan_file_capabilities, _imported_names, _archived_ids, _existing_markers
  Consider a shared protocol or base class
src/frob/vet/_obfuscation.py  suggestion  abstraction-opportunity
  4 functions share signature `(str) -> tuple[str, ...]`: high_entropy_strings, scan_text_obfuscation, _cwe_ids_from_body, enabling
  Consider a shared protocol or base class
src/frob/vet/_registry.py  suggestion  abstraction-opportunity
  3 functions share signature `(str, str, str) -> str`: _cache_key, _rewire_endpoint, _append_to_section
  Consider a shared protocol or base class
src/frob/serve/_tools.py  suggestion  abstraction-opportunity
  3 functions share signature `(Path, str) -> Result[dict, ServeError]`: frob_check_scope, frob_graph_query, frob_doc_for
  Consider a shared protocol or base class
src/frob/outline/__init__.py  suggestion  abstraction-opportunity
  6 functions share signature `(tuple[str, ...]) -> str`: _return_annotation, _md_row, _r1_hash, _r2_hash, _digest, _hash_tokens
  Consider a shared protocol or base class
src/frob/strata/_facts.py  suggestion  abstraction-opportunity
  4 functions share signature `(KernelModel) -> Result[None, StrataError]`: _validate_ids, _validate_levels, _validate_nonnegative_quantities, _validate_build_facts_preconditions
  Consider a shared protocol or base class
src/frob/strata/_lint.py  suggestion  abstraction-opportunity
  4 functions share signature `(Node) -> tuple[str, ...]`: node_flag_ids, node_pii_tags, _imports_python, _imports_c_family
  Consider a shared protocol or base class
src/frob/strata/_lint.py  suggestion  abstraction-opportunity
  3 functions share signature `(KernelModel) -> Result[tuple[LintViolation, ...], StrataError]`: check_lint_rate_limit, check_lint_cache_or_capacity, check_lint_fanin_capacity
  Consider a shared protocol or base class
src/frob/strata/_compliance.py  suggestion  abstraction-opportunity
  5 functions share signature `(KernelModel) -> tuple[ComplianceViolation, ...]`: _check_coppa, _check_erasure, _check_lawful_basis, _check_baa, _check_minimization
  Consider a shared protocol or base class
src/frob/strata/_code_binding.py  suggestion  abstraction-opportunity
  3 functions share signature `(CodeBinding) -> list[str]`: _sorted_owned_files, _sorted_owned_files, _sorted_owned_files
  Consider a shared protocol or base class
src/frob/strata/_breach.py  suggestion  abstraction-opportunity
  7 functions share signature `(KernelModel, dict[str, Node]) -> Result[None, StrataError]`: _validate_recovery_via, _validate_breach_preconditions, _validate_recovery_sources, _validate_no_hang, _validate_endorsement_chain, _validate_canary_levels, _validate_deploy_contracts
  Consider a shared protocol or base class
src/frob/strata/_effects.py  suggestion  abstraction-opportunity
  4 functions share signature `(Node) -> frozenset[str]`: _declared_kinds, node_may_kinds, node_allowed_syscalls, _node_capabilities
  Consider a shared protocol or base class
src/frob/strata/_selfconform.py  suggestion  abstraction-opportunity
  4 functions share signature `(KernelModel, CodeBinding, Path) -> list[SelfConformViolation]`: _core_undeclared_violations, _extended_kind_violations, _stale_design_violations, _collect_sys_violations
  Consider a shared protocol or base class
src/frob/strata/_pii.py  suggestion  abstraction-opportunity
  8 functions share signature `(Node) -> bool`: node_carries_pii, _is_trailing_comment, _has_static, _has_const_qualifier, _rust_has_pub, _rust_pyo3_export, _py_is_complex, _cpp_is_complex
  Consider a shared protocol or base class
src/frob/strata/_pii.py  suggestion  abstraction-opportunity
  4 functions share signature `(KernelModel) -> tuple[PiiViolation, ...]`: check_pii_catalog, check_pii_boundary_protection, check_pii_retention_erasure, check_pii_undeclared_flow
  Consider a shared protocol or base class
src/frob/strata/_scenarios.py  suggestion  abstraction-opportunity
  3 functions share signature `(KernelModel, str) -> list[str]`: _compromised_user_nodes, _flows_into, _flows_out_of
  Consider a shared protocol or base class
src/frob/strata/_host_isolation.py  suggestion  abstraction-opportunity
  3 functions share signature `(str, list[str], str, list[str], dict[str, HostManifest], int) -> tuple[list[Flow], int]`: _writable_path_movement_flows, _shared_port_movement_flows, _movement_flows_for_pair
  Consider a shared protocol or base class
src/frob/strata/_export.py  suggestion  abstraction-opportunity
  7 functions share signature `(KernelModel) -> str`: export_k8s_netpol, export_seccomp, export_iam, manifest_digest, generate_install_script, generate_status_script, generate_uninstall_script
  Consider a shared protocol or base class
src/frob/strata/_elaborate.py  suggestion  abstraction-opportunity
  9 functions share signature `(Module) -> Result[None, StrataError]`: _validate_scenarios, _validate_no_duplicates, _validate_waivers, _validate_references, _validate_boundary_phases, _validate_operations, _validate_observability, _validate_krb, _run_elaborate_validators
  Consider a shared protocol or base class
src/frob/strata/_elaborate.py  suggestion  abstraction-opportunity
  3 functions share signature `(Module) -> tuple[Flow, ...]`: _elaborate_boundary_phase_flows, _elaborate_operation_flows, _elaborate_observe_flows
  Consider a shared protocol or base class
src/frob/strata/_elaborate.py  suggestion  abstraction-opportunity
  4 functions share signature `(Module, KernelModel) -> Result[KernelModel, StrataError]`: _elaborate_refines, _expand_model_infra, _expand_model_secrets, _elaborate_expanded_model
  Consider a shared protocol or base class
src/frob/strata/_claims.py  suggestion  abstraction-opportunity
  3 functions share signature `(FactBase, Claim, BoundClaim) -> Result[ClaimResult, StrataError]`: _eval_bound_age, _eval_bound_rate, _eval_bound_latency_or_size
  Consider a shared protocol or base class
src/frob/lang/_walk_typescript.py  suggestion  abstraction-opportunity
  4 functions share signature `(Node, tuple[str, ...], list[RawSymbol]) -> None`: _visit, _visit, _recurse_trait, _recurse_impl
  Consider a shared protocol or base class
src/frob/lang/_walk_typescript.py  suggestion  abstraction-opportunity
  6 functions share signature `(Node) -> tuple[RawSymbol, ...]`: _walk_typescript, _walk_python, _walk_c, _walk_cpp, _walk_tsx, _walk_rust
  Consider a shared protocol or base class
src/frob/lang/_walk_python.py  suggestion  abstraction-opportunity
  5 functions share signature `(Node) -> str | None`: _const_assignment_name, _rust_test_macro_name, _enclosing_class_cpp, _first_identifier, _enclosing_class_py
  Consider a shared protocol or base class
src/frob/lang/_extract.py  suggestion  abstraction-opportunity
  7 functions share signature `(Node) -> None`: walk, visit, visit, visit, walk, visit, visit
  Consider a shared protocol or base class
src/frob/lang/_extract.py  suggestion  abstraction-opportunity
  6 functions share signature `(Node) -> int`: _effective_end_row, _py_function_line_count, _py_cyclomatic, _py_max_nesting, _cpp_max_nesting, _cpp_cyclomatic
  Consider a shared protocol or base class
src/frob/lang/_walk_c.py  suggestion  abstraction-opportunity
  5 functions share signature `(Node) -> str`: _find_declarator_name, _typedef_name, _cpp_declarator_name, _annotation_text, _cpp_func_name
  Consider a shared protocol or base class
src/frob/arch/_python.py  suggestion  abstraction-opportunity
  5 functions share signature `(object, str, int, list[ArchSuggestion]) -> None`: _check_long_functions, _check_god_classes, _check_deep_nesting, _check_long_functions, _check_god_classes
  Consider a shared protocol or base class
src/frob/arch/_python.py  suggestion  abstraction-opportunity
  13 functions share signature `(Node, set[str]) -> None`: _collect_dispatch_refs, _harvest_cpp_param, _harvest_cpp_declarator_name, _collect_assigned_names_cpp, _harvest_cpp_for, _harvest_param, _collect_param_names, _harvest_assignment, _harvest_binding_stmt, _harvest_with_item, _harvest_with, _collect_assigned_names, _harvest_pattern
  Consider a shared protocol or base class
src/frob/process/parsers/pytest.py  suggestion  abstraction-opportunity
  4 functions share signature `(str) -> Diagnostic | None`: _location_diagnostic, _leak_diagnostic, _cargo_json_diagnostic, _single_line_diagnostic
  Consider a shared protocol or base class
src/frob/process/parsers/pytest.py  suggestion  abstraction-opportunity
  11 functions share signature `(str, int) -> ToolResult`: parse_pytest, parse_ruff_json, parse_ruff_text, parse_ruff, parse_valgrind, _parse_text, _parse_xml, parse_eslint, parse_tsc, parse_clang_tidy, parse_ty
  Consider a shared protocol or base class
src/frob/deploy/_generate.py  suggestion  abstraction-opportunity
  4 functions share signature `(ManifestEntry) -> str`: _render_unit_file, _install_unit_block, _status_unit_block, _uninstall_unit_block
  Consider a shared protocol or base class
src/frob/deploy/_generate.py  suggestion  abstraction-opportunity
  4 functions share signature `(HostManifest) -> str`: _install_user_block, _install_owns_block, _uninstall_owns_block, _uninstall_user_block
  Consider a shared protocol or base class
src/frob/tickets/__init__.py  suggestion  abstraction-opportunity
  3 functions share signature `(Path) -> Result[dict[str, Ticket], TicketError]`: _load_merged, load_all, load_archive
  Consider a shared protocol or base class
src/frob/tickets/__init__.py  suggestion  abstraction-opportunity
  4 functions share signature `(Path) -> Result[int, TicketError]`: migrate, archive, renumber, migrate_to_ledger
  Consider a shared protocol or base class
src/frob/dup/_pipeline.py  suggestion  abstraction-opportunity
  3 functions share signature `(_FpState, GraphSnapshot, frozenset[str] | None, set[frozenset[str]]) -> list[tuple[ClonePair, ...]]`: _hash_rung_groups, _r4_groups, _r5_groups
  Consider a shared protocol or base class
src/frob/dup/_pipeline.py  suggestion  abstraction-opportunity
  4 functions share signature `(_FpState, str, str) -> bool`: _nicad_size_ratio_ok, _oreo_metric_ratio_ok, _deckard_vector_ok, _passes_r4_prefilters
  Consider a shared protocol or base class
src/frob/dup/_pipeline.py  suggestion  abstraction-opportunity
  6 functions share signature `(Any, Any, dict[str, Any]) -> Any`: _smt_translate, _smt_translate_simple, _smt_unaryop, _smt_binop, _smt_boolop, _smt_compare
  Consider a shared protocol or base class
src/frob/graph/digest.py  suggestion  abstraction-opportunity
  3 functions share signature `(RawSymbol) -> str`: digest_sig, digest_body, digest_doc
  Consider a shared protocol or base class
src/frob/graph/cache.py  suggestion  abstraction-opportunity
  3 functions share signature `(Path) -> sqlite3.Connection`: _open, connect, connect_readonly
  Consider a shared protocol or base class
src/frob/app/gitlog_runner.py  suggestion  abstraction-opportunity
  40 functions share signature `(AppConfig) -> None`: run, run, run, run, run, _profile, _heat, _print_heat_result, _heat_body, run, run, run, _run_generate, _require_audit_flags, _run_audit, run, run, _report_check_result, run, __init__, _warn_facet_informational, run, run, _require_land_args, run, _fall_back_to_map, run, run, run, run, run, run, run, run, run, _run_plan, _run_export, _run_doc, _run_audit, run
  Consider a shared protocol or base class
src/frob/app/vet_runner.py  suggestion  abstraction-opportunity
  17 functions share signature `(Path, AppConfig) -> None`: _run_scan, _run_stamp_baseline, _new, _list, _show, _doable, _renumber, _renumber_one, _land, _plan, _start, _sweep_cmd, _attach, _block, _close, _fail, _evidence
  Consider a shared protocol or base class
src/frob/app/perf_runner.py  suggestion  abstraction-opportunity
  5 functions share signature `(AppConfig, Path)`: _ranked_heat_entries, _dispatch_check_cpp, _dispatch_check_rust, _dispatch_check_ts, _dispatch_check_python
  Consider a shared protocol or base class
src/frob/app/dup_runner.py  suggestion  abstraction-opportunity
  6 functions share signature `(AppConfig, Path) -> None`: _probe, _acknowledge_and_write, _run_selected_and_report, _run_search, _run_overview, _run_extract
  Consider a shared protocol or base class
src/frob/app/deploy_runner.py  suggestion  abstraction-opportunity
  3 functions share signature `(Path) -> KernelModel | None`: _load_model, _load_export_model, _load_audit_model
  Consider a shared protocol or base class
src/frob/app/check_runner.py  suggestion  abstraction-opportunity
  3 functions share signature `(AppConfig, Path) -> CheckResult`: _run_auto_detected_stages, _run_pinned_stage, _run_all_stages
  Consider a shared protocol or base class
src/frob/app/_style.py  suggestion  abstraction-opportunity
  7 functions share signature `(str, bool) -> str`: style_ticket_id, style_state, style_ok, style_fail, style_warn, style_header, style_rule
  Consider a shared protocol or base class
src/frob/app/sys_runner.py  suggestion  abstraction-opportunity
  4 functions share signature `(AuditReport) -> None`: _log_waived_gaps, _log_proved_summary, _log_gaps, _print_audit_report
  Consider a shared protocol or base class
src/frob/app/sys_runner.py  suggestion  abstraction-opportunity
  4 functions share signature `(SelfConformReport) -> None`: _log_waived_selfconform, _log_selfconform_proved, _log_selfconform_violations, _print_selfconform_report
  Consider a shared protocol or base class CLI via arch_runner/AppConfig overrides -- it was never wired into the GATE path, and there is no [arch] section in frob.toml. Result: the gate flags large-file at 500 and long-function at the default, contradicting the user's own disclosed calibration decision. Fix: add an [arch] frob.toml section (max_function_lines, max_class_methods, max_file_lines, max_nesting_depth, max_local_imports) read via AppConfig/config.py, thread it into analyze_project from BOTH arch_gate and the whole frob check path (not just the standalone CLI), defaulting to the calibrated 60/800/etc. This is HONORING an already-made user decision, NOT threshold-loosening -- disclose the defaults in frob.toml + docs. Expect large-file (34) and long-function findings to drop to the intended calibrated level; genuinely >800-line modules remain a separate refactor decision. Add tests: a 600-line file flagged at default-500 but NOT at configured-800; frob.toml [arch] override respected by the gate. Update docs/modules/arch.md + gates.md.