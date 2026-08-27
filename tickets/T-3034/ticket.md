---
id: T-3034
title: 26 uncharacterized Linux test failures need per-test triage
state: done
kind: bug
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/system/test_cli_evidence_enforcement.py
- tests/system/test_cli_graph.py
- tests/test_app_daemon_proxy.py
- tests/test_clean.py
- tests/test_dup_smart.py
- tests/test_gates.py
- tests/test_gates_tick009_tick010.py
- tests/test_makefile_lock_sync.py
- tests/test_stats.py
- tests/unit/test_app_runners_batch7.py
- tests/unit/test_app_runners_t0714_doable_summary.py
- tests/unit/test_app_runners_t1822_already_landed.py
- tests/unit/test_coordinator_scripts.py
- tests/unit/test_exports.py
- tests/unit/test_gitattributes_merge.py
- tests/unit/test_new_ticket_scope_breadth_ack_flag.py
scope_breadth_ack: true
scope_breadth_ack_reason: T-3034 is a per-test triage ticket over 26 failures scattered
  across tests/; the real touched set is not knowable until each is individually triaged,
  narrowing after the fact once known
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/
  reason: 'T-3034: narrow to the 26 named failing tests'' own files, avoiding collision
    with T-3116''s lease on test_ticket_land_ty_diff_attribution.py'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/system/test_cli_evidence_enforcement.py
  reason: 'T-3034: narrow to the 26 named failing tests'' own files, avoiding collision
    with T-3116''s lease on test_ticket_land_ty_diff_attribution.py'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/system/test_cli_graph.py
  reason: 'T-3034: narrow to the 26 named failing tests'' own files, avoiding collision
    with T-3116''s lease on test_ticket_land_ty_diff_attribution.py'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/test_app_daemon_proxy.py
  reason: 'T-3034: narrow to the 26 named failing tests'' own files, avoiding collision
    with T-3116''s lease on test_ticket_land_ty_diff_attribution.py'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/test_clean.py
  reason: 'T-3034: narrow to the 26 named failing tests'' own files, avoiding collision
    with T-3116''s lease on test_ticket_land_ty_diff_attribution.py'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/test_dup_smart.py
  reason: 'T-3034: narrow to the 26 named failing tests'' own files, avoiding collision
    with T-3116''s lease on test_ticket_land_ty_diff_attribution.py'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/test_gates.py
  reason: 'T-3034: narrow to the 26 named failing tests'' own files, avoiding collision
    with T-3116''s lease on test_ticket_land_ty_diff_attribution.py'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/test_gates_tick009_tick010.py
  reason: 'T-3034: narrow to the 26 named failing tests'' own files, avoiding collision
    with T-3116''s lease on test_ticket_land_ty_diff_attribution.py'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/test_makefile_lock_sync.py
  reason: 'T-3034: narrow to the 26 named failing tests'' own files, avoiding collision
    with T-3116''s lease on test_ticket_land_ty_diff_attribution.py'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/test_stats.py
  reason: 'T-3034: narrow to the 26 named failing tests'' own files, avoiding collision
    with T-3116''s lease on test_ticket_land_ty_diff_attribution.py'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/unit/test_app_runners_batch7.py
  reason: 'T-3034: narrow to the 26 named failing tests'' own files, avoiding collision
    with T-3116''s lease on test_ticket_land_ty_diff_attribution.py'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/unit/test_app_runners_t0714_doable_summary.py
  reason: 'T-3034: narrow to the 26 named failing tests'' own files, avoiding collision
    with T-3116''s lease on test_ticket_land_ty_diff_attribution.py'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/unit/test_app_runners_t1822_already_landed.py
  reason: 'T-3034: narrow to the 26 named failing tests'' own files, avoiding collision
    with T-3116''s lease on test_ticket_land_ty_diff_attribution.py'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/unit/test_coordinator_scripts.py
  reason: 'T-3034: narrow to the 26 named failing tests'' own files, avoiding collision
    with T-3116''s lease on test_ticket_land_ty_diff_attribution.py'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/unit/test_exports.py
  reason: 'T-3034: narrow to the 26 named failing tests'' own files, avoiding collision
    with T-3116''s lease on test_ticket_land_ty_diff_attribution.py'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/unit/test_gitattributes_merge.py
  reason: 'T-3034: narrow to the 26 named failing tests'' own files, avoiding collision
    with T-3116''s lease on test_ticket_land_ty_diff_attribution.py'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/unit/test_new_ticket_scope_breadth_ack_flag.py
  reason: 'T-3034: narrow to the 26 named failing tests'' own files, avoiding collision
    with T-3116''s lease on test_ticket_land_ty_diff_attribution.py'
  actor: logan
  at: '2026-08-27'
evidence:
- tests/system/test_cli_graph.py::TestAck::test_ack_then_requery_clean
- tests/system/test_cli_graph.py::TestAck::test_ack_then_drift_after_change
- tests/system/test_cli_evidence_enforcement.py::TestCliEvidenceEnforcementEndToEnd::test_docs_kind_cmd_evidence_path_still_works
- tests/test_dup_smart.py::TestFindClones::test_core_unavailable_is_honest_err_not_silent_downgrade
- tests/test_gates.py::TestAutofixManifest::test_killed_mid_handler_leaves_manifest_naming_completed_fixes
- tests/test_gates.py::TestOptInGates::test_perf_gate_still_reports_genuine_parse_failure
- tests/test_gates.py::TestFixEngineTierABatch2::test_docenum001_fails_before_fix_and_passes_after
- tests/test_gates_tick009_tick010.py::TestTick009ScopeBreadthNudges::test_chronically_over_broad_glob_warns
- tests/test_gates_tick009_tick010.py::TestTick009ScopeBreadthNudges::test_in_progress_over_broad_glob_still_warns
- tests/unit/test_app_runners_batch7.py::TestTicketStart::test_start_refuses_over_broad_scope
- tests/unit/test_app_runners_t0714_doable_summary.py::TestRenderScopeBreadthSummary::test_multiple_stale_leases_collapse_to_one_summary_line
- tests/unit/test_new_ticket_scope_breadth_ack_flag.py::TestScopeBreadthAckFlag::test_unacknowledged_broad_scope_still_warns
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: f3286496031e05e199561c4dfa229a00370db3af
---
Linux full-suite triage (T-2992): 26 residual failures with no shared
root cause identified yet (each was spot-checked or grouped by name
similarity only, not individually root-caused against source, given the
size of this drive). One IS root-caused
(tests/unit/test_gitattributes_merge.py::TestAttachmentCrlfSuppression::test_unrelated_text_file_still_gets_autocrlf_conversion,
which depends on this box's global git `core.autocrlf` setting -- likely
environment-dependent test fragility, not a product defect, but not
independently verified by disabling/enabling the setting here).

This ticket exists so all 26 have a home and are not silently dropped;
each needs its own dedicated triage pass (read the actual assertion
failure, determine product-defect vs test-fragility, then either fix or
split into its own ticket). Do NOT batch-fix these without reading each
one individually -- they were deliberately NOT root-caused here to stay
inside T-2992's own budget (a large uncharacterized-but-FILED residual is
the honest outcome the parent ticket asks for, not a rushed guess).

RESIDUAL (26), one per line, ` - AssertionError: asse...`/` - assert...`
suffixes are truncated pytest -q summary text, not part of the node id:
  tests/system/test_cli_evidence_enforcement.py::TestCliEvidenceEnforcementEndToEnd::test_close_fails_on_unrelated_evidence
  tests/system/test_cli_evidence_enforcement.py::TestCliEvidenceEnforcementEndToEnd::test_docs_kind_cmd_evidence_path_still_works
  tests/system/test_cli_graph.py::TestAck::test_ack_then_drift_after_change
  tests/system/test_cli_graph.py::TestAck::test_ack_then_requery_clean
  tests/test_app_daemon_proxy.py::TestDifferentialParity::test_check_delta_gates_only_json_daemon_matches_in_process
  tests/test_clean.py::test_makefile_coverage_recipe_never_escalates_clean_tier
  tests/test_dup_smart.py::TestFindClones::test_core_unavailable_is_honest_err_not_silent_downgrade
  tests/test_gates.py::TestAutofixManifest::test_killed_mid_handler_leaves_manifest_naming_completed_fixes
  tests/test_gates.py::TestDoc004ConsoleCommandDrift::test_real_subcommand_unanchored_warns_unbound
  tests/test_gates.py::TestFixEngineTierA::test_excluded_handler_is_skipped_and_file_untouched
  tests/test_gates.py::TestFixEngineTierABatch2::test_docenum001_fails_before_fix_and_passes_after
  tests/test_gates.py::TestOptInGates::test_perf_gate_still_reports_genuine_parse_failure
  tests/test_gates.py::TestRuleFixability::test_checked_in_literal_matches_a_fresh_scan
  tests/test_gates.py::TestWireGate::test_new_cli_dest_present_in_config_external_is_not_flagged
  tests/test_gates_tick009_tick010.py::TestTick009ScopeBreadthNudges::test_chronically_over_broad_glob_warns
  tests/test_gates_tick009_tick010.py::TestTick009ScopeBreadthNudges::test_in_progress_over_broad_glob_still_warns
  tests/test_makefile_lock_sync.py::test_upload_commits_uv_lock_with_pyproject
  tests/test_makefile_lock_sync.py::test_upload_relocks_after_version_bump
  tests/test_stats.py::test_collect_combines_both - AssertionError: asse...
  tests/unit/test_app_runners_batch7.py::TestTicketStart::test_start_refuses_over_broad_scope
  tests/unit/test_app_runners_t0714_doable_summary.py::TestRenderScopeBreadthSummary::test_multiple_stale_leases_collapse_to_one_summary_line
  tests/unit/test_app_runners_t1822_already_landed.py::TestRenderAlreadyLandedMarkers::test_no_markers_prints_nothing_and_returns_empty
  tests/unit/test_coordinator_scripts.py::TestInProgressTicketScopeLeasesLiveGit::test_live_worktree_with_lease_file_removed_is_not_leaked
  tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols
  tests/unit/test_gitattributes_merge.py::TestAttachmentCrlfSuppression::test_unrelated_text_file_still_gets_autocrlf_conversion
  tests/unit/test_new_ticket_scope_breadth_ack_flag.py::TestScopeBreadthAckFlag::test_unacknowledged_broad_scope_still_warns