---
id: T-4419
title: Clean tests/unit docstrings of change-narrative (DOCARCH001)
state: done
kind: docs
origin: human
created: '2026-09-11'
priority: medium
parent: T-2994
tier: story
sprint: v0.534.0
runs_last: false
milestone: 0.534.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_ticket_runner_gate_findings.py
- tests/unit/test_conftest_sigbreak_faulthandler.py
- tests/unit/test_graph_cache.py
- tests/unit/strata/test_threat.py
- tests/unit/test_makefile_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_ticket_runner_gate_findings.py
  reason: narrow to cluster 0 (32 DOCARCH001 findings, 5 files) per split plan
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/unit/test_conftest_sigbreak_faulthandler.py
  reason: narrow to cluster 0 (32 DOCARCH001 findings, 5 files) per split plan
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/unit/test_graph_cache.py
  reason: narrow to cluster 0 (32 DOCARCH001 findings, 5 files) per split plan
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/unit/strata/test_threat.py
  reason: narrow to cluster 0 (32 DOCARCH001 findings, 5 files) per split plan
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/unit/test_makefile_coverage.py
  reason: narrow to cluster 0 (32 DOCARCH001 findings, 5 files) per split plan
  actor: logan
  at: '2026-09-19'
triage_changes:
- field: sprint
  old_value: v0.533.0
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-16'
- field: milestone
  old_value: 0.533.0
  new_value: 0.534.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-16'
body_changes:
- mode: append
  reason: re-measure DOCARCH001 denominator per subdir, plan clusters/child tickets
  actor: logan
  at: '2026-09-19'
  old_length: 220
  new_length: 5983
- mode: append
  reason: record filed child ticket ids after split
  actor: logan
  at: '2026-09-19'
  old_length: 5983
  new_length: 6321
- mode: append
  reason: record promoted ids after fleet land squash renumbered the child tickets
  actor: logan
  at: '2026-09-19'
  old_length: 6321
  new_length: 6568
evidence:
- tests/gates/test_docstring_archaeology.py::TestDocarch001Violations::test_ticket_plus_narrative_wording_warns
- tests/gates/test_docstring_archaeology.py::TestDocarch001Violations::test_bare_ticket_reference_stays_quiet
designated_repro_test: null
acceptance:
- text: Given a scoped frob check on the 5 files in cluster 0 (tests/unit/test_ticket_runner_gate_findings.py,
    tests/unit/test_conftest_sigbreak_faulthandler.py, tests/unit/test_graph_cache.py,
    tests/unit/strata/test_threat.py, tests/unit/test_makefile_coverage.py), when
    DOCARCH001 is measured, then its finding count for those files is 0
  evidence:
  - tests/gates/test_docstring_archaeology.py::TestDocarch001Violations::test_ticket_plus_narrative_wording_warns
  - tests/gates/test_docstring_archaeology.py::TestDocarch001Violations::test_bare_ticket_reference_stays_quiet
acceptance_amendments:
- op: replace
  index: 1
  old_text: Given a full frob check on tests/unit, when DOCARCH001 is measured, then
    its finding count for tests/unit is 0
  new_text: Given a scoped frob check on the 5 files in cluster 0 (tests/unit/test_ticket_runner_gate_findings.py,
    tests/unit/test_conftest_sigbreak_faulthandler.py, tests/unit/test_graph_cache.py,
    tests/unit/strata/test_threat.py, tests/unit/test_makefile_coverage.py), when
    DOCARCH001 is measured, then its finding count for those files is 0
  reason: narrowed scope to cluster 0 per the split plan; the other 5 clusters (177
    findings) are covered by child tickets
  actor: logan
  at: '2026-09-19'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
DOCARCH001 measured 166 findings in tests/unit on a full check today (2026-09-11). Rewrite each flagged docstring to state WHAT the test verifies, not the ticket/change narrative behind it. Denominator: 166 (tests/unit).


## Re-measurement 2026-09-19 (direct docarch001_violations(root) call, dev base)

Prior denominator (166, measured 2026-09-11) is stale. Full re-count on tests/unit:
TOTAL = 182 findings.

Per-subdirectory breakdown:
- tests/unit (top-level files): 113
- tests/unit/strata: 26
- tests/unit/rapid_sweep_suite: 11
- tests/unit/gates: 10
- tests/unit/coordinator_suite: 8
- tests/unit/graph: 4
- tests/unit/verify: 4
- tests/unit/arch_suite: 3
- tests/unit/perf: 2
- tests/unit/vet: 1

2 files excluded from all clustering because they are leased by in-progress tickets
(grep -l against .git/frob-leases/*.json):
- tests/unit/verify/test_verify_runner.py (1 finding) -- leased by T-3082
- tests/unit/strata/test_selfconform.py (4 findings) -- leased by T-4633
These 5 findings are DEFERRED, not dropped: pick them up once T-3082 / T-4633 land.

Remaining 177 findings split into 6 clusters of ~30-33 each (file-granular, no file split
across clusters). T-4419 itself is narrowed to cluster 0 (32 findings, 5 files). The other
5 clusters are filed as child tickets (kind=docs, parent T-4419, acceptance "DOCARCH001
count for <files> is 0"):

Cluster 0 (T-4419, this ticket) -- 32 findings, 5 files:
  tests/unit/test_ticket_runner_gate_findings.py (8)
  tests/unit/test_conftest_sigbreak_faulthandler.py (7)
  tests/unit/test_graph_cache.py (7)
  tests/unit/strata/test_threat.py (5)
  tests/unit/test_makefile_coverage.py (5)

Cluster 1 -- 32 findings, 9 files:
  tests/unit/coordinator_suite/test_fleet_worktrees.py (4)
  tests/unit/test_app_runners_batch7.py (4)
  tests/unit/test_check_budget.py (4)
  tests/unit/test_ticket_runner_ledger_mirror.py (4)
  tests/unit/test_ticket_store.py (4)
  tests/unit/graph/test_dsl_markdown_waive.py (3)
  tests/unit/rapid_sweep_suite/test_filing.py (3)
  tests/unit/rapid_sweep_suite/test_sweep_run.py (3)
  tests/unit/test_check.py (3)

Cluster 2 -- 33 findings, 16 files:
  tests/unit/test_process_lock.py (3)
  tests/unit/coordinator_suite/test_fleet_report.py (2)
  tests/unit/gates/test_deprecated_baseline.py (2)
  tests/unit/gates/test_wire001_cli_dest_semantic.py (2)
  tests/unit/perf/test_hotpath_smells.py (2)
  tests/unit/rapid_sweep_suite/test_attribution.py (2)
  tests/unit/strata/test_contention.py (2)
  tests/unit/strata/test_cve_fingerprint.py (2)
  tests/unit/strata/test_effects.py (2)
  tests/unit/strata/test_facts.py (2)
  tests/unit/strata/test_native_staleness.py (2)
  tests/unit/test_arch_srp.py (2)
  tests/unit/test_cli_group_parity.py (2)
  tests/unit/test_conftest_stackdump.py (2)
  tests/unit/test_dup_legacy_cpp.py (2)
  tests/unit/test_gitattributes_merge.py (2)

Cluster 3 -- 33 findings, 21 files:
  tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py (2)
  tests/unit/test_land_in_progress_window.py (2)
  tests/unit/test_land_verify_claim_divergence_sentinel.py (2)
  tests/unit/test_lang_strata.py (2)
  tests/unit/test_main_entry.py (2)
  tests/unit/test_policy_weakening_gate.py (2)
  tests/unit/test_process_reap.py (2)
  tests/unit/test_release_workflow_gate.py (2)
  tests/unit/test_skills_sync.py (2)
  tests/unit/test_ticket_runner_land_release.py (2)
  tests/unit/test_unlanded_branch_work.py (2)
  tests/unit/verify/test_worker.py (2)
  tests/unit/arch_suite/test_concurrency.py (1)
  tests/unit/arch_suite/test_dispatch.py (1)
  tests/unit/arch_suite/test_lang_adapters.py (1)
  tests/unit/coordinator_suite/test_fleet_host_load.py (1)
  tests/unit/coordinator_suite/test_fleet_land.py (1)
  tests/unit/gates/test_detector_scope.py (1)
  tests/unit/gates/test_examined_sites.py (1)
  tests/unit/gates/test_exhaustive_handling_path_shape.py (1)
  tests/unit/gates/test_ffi_boundary_path_shape.py (1)

Cluster 4 -- 33 findings, 33 files (all weight-1):
  tests/unit/gates/test_lexical_selfcheck.py
  tests/unit/gates/test_sys_selfaudit.py
  tests/unit/graph/test_dsl.py
  tests/unit/rapid_sweep_suite/test_baseline.py
  tests/unit/rapid_sweep_suite/test_commit.py
  tests/unit/rapid_sweep_suite/test_dispose.py
  tests/unit/strata/test_audit.py
  tests/unit/strata/test_claims.py
  tests/unit/strata/test_fragments.py
  tests/unit/strata/test_mode_conformance.py
  tests/unit/strata/test_parse.py
  tests/unit/strata/test_strata_core_gil.py
  tests/unit/strata/test_vmodel_authoring.py
  tests/unit/test_app_runners_batch6.py
  tests/unit/test_app_runners_json_guard_t2492.py
  tests/unit/test_artifact_smoke_script.py
  tests/unit/test_check_tool_unavailable.py
  tests/unit/test_claims_and_store_batch6.py
  tests/unit/test_conftest_suite_result_status.py
  tests/unit/test_cycle_runner_doc_waiver_t2598.py
  tests/unit/test_cycle_waiver.py
  tests/unit/test_docs_module.py
  tests/unit/test_doctor_runner_t1276.py
  tests/unit/test_done_report_check_scope.py
  tests/unit/test_dup_cache.py
  tests/unit/test_findings_severity_pinned.py
  tests/unit/test_frob_core_gil.py
  tests/unit/test_gitattributes_crlf_normalization.py
  tests/unit/test_graph_ingest_batching.py
  tests/unit/test_graph_stat_trust_margin.py
  tests/unit/test_land_compose.py
  tests/unit/test_land_sibling_regression.py
  tests/unit/test_land_squash_residue_reclaim.py

Cluster 5 -- 14 findings, 14 files (all weight-1):
  tests/unit/test_land_stage_flip.py
  tests/unit/test_lang_parse_guard.py
  tests/unit/test_logging_quiet.py
  tests/unit/test_memo.py
  tests/unit/test_new_ticket_scope_overlap_warning.py
  tests/unit/test_process_pid_liveness.py
  tests/unit/test_pyfmt_runner.py
  tests/unit/test_rel002_dev_suffix.py
  tests/unit/test_scaffold_natives_shim.py
  tests/unit/test_scaffold_project.py
  tests/unit/test_ticket_new_related.py
  tests/unit/test_waive_audit_watermark.py
  tests/unit/verify/test_backpressure.py
  tests/unit/vet/test_capability_modes.py


Filed child tickets for clusters 1-5 (kind=docs, parent T-4419): T-4632 (cluster 1), T-4630 (cluster 2), T-4628 (cluster 3), T-4631 (cluster 4), T-4629 (cluster 5, also carries the 2 leased-file deferrals). T-4419 itself is narrowed to cluster 0 (32 findings, 5 files, scope set above).

Renumbered by a land squash (T-4524, commit ade7d9db3): T-4632->T-4632 (cluster 1), T-4630->T-4630 (cluster 2), T-4628->T-4628 (cluster 3), T-4631->T-4631 (cluster 4), T-4629->T-4629 (cluster 5).