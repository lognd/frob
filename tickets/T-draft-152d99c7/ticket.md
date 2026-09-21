---
id: T-draft-152d99c7
title: 'post-land sweep regression from T-3614: 6 new (rule, file) identit(ies), 19
  finding(s) (DRIFT001, DUP001, DUP002, PERF012)'
state: queued
kind: bug
origin: agent
created: '2026-09-21'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/_cli_parsers/_ticket/_new.py
- tests/narrative/test_bulk.py
- tests/unit/test_leases_staleness_perf.py
- tests/unit/test_ticket_verbs_wait.py
findings:
- - DRIFT001
  - src/frob/_cli_parsers/_ticket/_new.py
- - DUP001
  - tests/narrative/test_bulk.py
- - DUP001
  - tests/unit/test_ticket_verbs_wait.py
- - DUP002
  - tests/narrative/test_bulk.py
- - DUP002
  - tests/unit/test_leases_staleness_perf.py
- - PERF012
  - tests/unit/test_ticket_verbs_wait.py
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
The deferred post-land unscoped sweep (T-1684) for T-3614 at commit 2bae40c0001fc5741fed34ceab03d961868cd42f found 199 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (6), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 19 actual finding(s) across those 6 identit(ies).

New (rule, file) identit(ies) filed here:

- DRIFT001  src/frob/_cli_parsers/_ticket/_new.py
- DUP001  tests/narrative/test_bulk.py
- DUP001  tests/unit/test_ticket_verbs_wait.py
- DUP002  tests/narrative/test_bulk.py
- DUP002  tests/unit/test_leases_staleness_perf.py
- PERF012  tests/unit/test_ticket_verbs_wait.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- COV002  src/frob/_cli_parsers/_ticket/_new.py  -> attributed to T-3614 (commit 2bae40c0001f, already closed/dropped -- filed below) via src/frob/_cli_parsers/_ticket/_closeout_evidence.py::_add_ticket_fail_evidence_archive_parsers -> src/frob/_cli_parsers/_ticket/_new.py::_add_ticket_wait_arg -> src/frob/_cli_parsers/_ticket/_new.py::_TICKET_WAIT_DEFAULT_S
- COV002  src/frob/arch/_models.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/docs/__init__.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/dup/_legacy_cs.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/excludes.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/gates/_models.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/gates/_pii_structural/__init__.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/gates/_suppress.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/lang/_extract.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/lang/_walk_csharp.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/narrative/_cli.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/refactor/_transaction.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/strata/_audit.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/strata/_backpressure.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/strata/_compliance.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/strata/_mutation_audit.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/strata/_packs.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/strata/_unity_asmdef.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/testing/_dotnet_runner.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/tickets/_land_queue.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/tickets/_land_release.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/tickets/_worktree_sweep.py  -> attributed to T-4657 (commit a9788408753f, already closed/dropped -- filed below) via src/frob/tickets/_new_renumber.py::renumber -> src/frob/tickets/_new_renumber.py::_refuse_renumber_inside_worktree -> src/frob/tickets/_worktree_sweep.py::_is_agent_worktree_path
- COV002  src/frob/verify/_quarantine.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/vet/_capability_registry/_matrix.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/xref/__init__.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/gates_suite/test_coverage.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/system/test_artifact_smoke.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/system/test_cli_check.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/system/test_cli_doctor.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/system/test_fleet_status_ground_truth.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/system/test_frob_self_model.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/system/test_run_helper_env_leak.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/test_cache_gate.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/test_ci_workflow_matrix.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/test_coverage.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/test_docptr_gate.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/test_gate_cache.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/test_gates_suppress.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/test_gitio.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/test_graph.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/test_land_verify_claims_outcome.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/test_lang_conformance_gate.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/test_pii_structural_gate.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/test_refactor.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/test_release.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/test_scaffold_worktree_lease_hook.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/test_serve_daemon.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/test_testing.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/test_ticket_evidence.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/test_ticket_land_proof_claims.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/test_ticket_leases_cross_worktree.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/test_ticket_work_and_land_finish.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/test_tickets.py  -> attributed to T-4657 (commit a9788408753f, already closed/dropped -- filed below) via tests/test_tickets.py::TestTicketStartWarnsOnFindingDuplicate.test_start_warns_and_names_the_other_ticket -> src/frob/tickets/_new_renumber.py::_allocate_and_write_new_ticket -> src/frob/tickets/_new_renumber.py::_allocate_and_check_ticket_id -> src/frob/tickets/_new_renumber.py::_allocate_ticket_id
- COV002  tests/test_tickets_acceptance.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/test_tickets_cmd_evidence.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/test_tickets_collision.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/test_tickets_evidence_cli.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/test_tickets_lease.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/test_tickets_leases.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/test_tickets_migration.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/test_tickets_organization.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/test_tickets_parent.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/test_tickets_priority.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/test_tickets_velocity.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/test_waive_gate.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/ticket_land_suite/test_land_lock.py  -> attributed to T-5084 (commit 96b79c342c07, already closed/dropped -- filed below) via tests/ticket_land_suite/test_land_lock.py::TestLandLockHolderMetadataAndTimeout
- COV002  tests/ticket_land_suite/test_land_reaps_worktree.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/ticket_land_suite/test_verify_intent.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/arch_suite/test_concurrency.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/arch_suite/test_dispatch.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/arch_suite/test_lang_adapters.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/coordinator_suite/test_fleet_host_load.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/coordinator_suite/test_fleet_land.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/coordinator_suite/test_fleet_report.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/coordinator_suite/test_fleet_worktrees.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/gates/test_deprecated_baseline.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/gates/test_examined_sites.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/gates/test_lexical_selfcheck.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/graph/test_dsl_invariant_property.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/rapid_sweep_suite/test_attribution.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/rapid_sweep_suite/test_baseline.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/rapid_sweep_suite/test_commit.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/rapid_sweep_suite/test_dispose.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/rapid_sweep_suite/test_filing.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/rapid_sweep_suite/test_window.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/strata/test_facts.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/strata/test_selfconform.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/strata/test_strata_scan_cache.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/strata/test_threat.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_app_runners_batch5.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_app_runners_batch6.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_app_runners_batch7.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_app_runners_json_guard_t2492.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_artifact_smoke_script.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_check.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_check_budget.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_check_scoped_files.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_check_skip_flag.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_check_tool_unavailable.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_claims_and_store_batch6.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_cli_group_parity.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_conftest_sigbreak_faulthandler.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_conftest_stackdump.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_dev_branch_workflow.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_doctor_runner_t1276.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_done_report_check_scope.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_dup_cache.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_frob_core_gil.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_gitattributes_merge.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_graph_cache.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_graph_get_snapshot.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_graph_stat_trust_margin.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_land_cas_ledger_retry.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_land_compose.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_land_default_queue.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_land_leaked_tickets_lease_hoist.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_land_merge_conflict_drop.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_land_queue.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_land_sibling_regression.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_land_squash_residue_reclaim.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_land_stackdump.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_land_stage_flip.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_lang_parse_guard.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_lang_strata.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_lease_lifecycle.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_leases_staleness_perf.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_main_entry.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_makefile_coverage.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_new_ticket_scope_overlap_warning.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_policy_weakening_gate.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_process_lock.py  -> attributed to T-4657 (commit a9788408753f, already closed/dropped -- filed below) via tests/unit/test_process_lock.py::TestSharedIdCounterPlatformBackends.test_no_lock_primitive_refuses_loudly -> src/frob/tickets/_new_renumber.py::_allocate_ticket_id
- COV002  tests/unit/test_process_pid_liveness.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_process_reap.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_release_workflow_gate.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_scaffold_project.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_scaffold_unity_project.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_scope_closure_declared_scope_only.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_store_mode_memoization.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_support_csharp.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_suppress_worktree_path.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_telemetry_verb_recording.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_ticket_cli_surface.py  -> attributed to T-3614 (commit 2bae40c0001f, already closed/dropped -- filed below) via tests/unit/test_ticket_cli_surface.py::TestHiddenInternalCallbacks.test_sweep_async_absent_from_help -> tests/unit/test_ticket_cli_surface.py::_build_ticket_parser -> src/frob/_cli_parsers/_ticket/__init__.py::_add_ticket_parser -> src/frob/_cli_parsers/_ticket/__init__.py::_add_ticket_lifecycle_parsers -> src/frob/_cli_parsers/_ticket/__init__.py::_add_ticket_closeout_parsers -> src/frob/_cli_parsers/_ticket/_closeout_evidence.py::_add_ticket_fail_evidence_archive_parsers
- COV002  tests/unit/test_ticket_new_related.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_ticket_runner_gate_findings.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_ticket_runner_land_cmd_flags.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_ticket_runner_land_release.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_ticket_runner_ledger_mirror.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_ticket_store.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_unity_batchmode.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_unlanded_branch_work.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_xref.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/verify/test_backpressure.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/verify/test_quarantine.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/verify/test_verify_runner.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/verify/test_worker.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/vet_suite/test_scan_tree.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC011  docs/modules/gate-race001.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC012  docs/commands/  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DRIFT001  src/frob/_cli_parsers/_ticket/_new.py  -> attributed to T-3614 (commit 2bae40c0001f, already closed/dropped -- filed below) via src/frob/_cli_parsers/_ticket/_closeout_evidence.py::_add_ticket_fail_evidence_archive_parsers -> src/frob/_cli_parsers/_ticket/_new.py::_add_ticket_wait_arg -> src/frob/_cli_parsers/_ticket/_new.py::_TICKET_WAIT_DEFAULT_S
- DUP001  tests/narrative/test_bulk.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DUP001  tests/unit/test_ticket_verbs_wait.py  -> attributed to T-3614 (commit 2bae40c0001f, already closed/dropped -- filed below) via tests/unit/test_ticket_verbs_wait.py::TestDispatchWait.test_budget_exhausted_names_holder -> src/frob/app/ticket_runner/__init__.py::_refuse_if_land_in_progress_for_dispatch
- DUP002  tests/narrative/test_bulk.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DUP002  tests/unit/test_leases_staleness_perf.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- FLAGCOV001  frob.toml  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- INV003  docs/modules/gate-race001.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF012  tests/unit/test_ticket_verbs_wait.py  -> attributed to T-3614 (commit 2bae40c0001f, already closed/dropped -- filed below) via tests/unit/test_ticket_verbs_wait.py::TestDispatchWait.test_budget_exhausted_names_holder -> src/frob/app/ticket_runner/__init__.py::_refuse_if_land_in_progress_for_dispatch
- SELFAUDIT001  design  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- SYS003  src/frob/narrative/_bulk.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TEST001  src/frob/narrative/_bulk.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-3032.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-3899.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-3936.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-3962.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-3964.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-3986.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-3995.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-3997.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4030.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4112.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4113.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4115.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4254.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4420.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4509.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4612.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4657.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4658.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4661.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4760.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4951.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4991.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4993.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-5124.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-5125.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-5126.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- WIRE001  src/frob/_cli_parsers/_ticket/_new.py  -> attributed to T-3614 (commit 2bae40c0001f, already closed/dropped -- filed below) via src/frob/_cli_parsers/_ticket/_closeout_evidence.py::_add_ticket_fail_evidence_archive_parsers -> src/frob/_cli_parsers/_ticket/_new.py::_add_ticket_wait_arg -> src/frob/_cli_parsers/_ticket/_new.py::_TICKET_WAIT_DEFAULT_S
- WIRE001  src/frob/narrative/_bulk.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- WIRE001  src/frob/tickets/_land.py  -> attributed to T-5084 (commit 96b79c342c07, already closed/dropped -- filed below) via src/frob/tickets/_land.py::_prune_dead_land_status_entries
- WIRE001  tests/narrative/test_bulk.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.