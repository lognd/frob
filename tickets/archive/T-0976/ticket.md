---
id: T-0976
title: 'ARCH001 burn-down: remaining 47 long-function findings'
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/**
- frob.toml
- frob.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: frob.toml
  reason: 'T-0976 promotes ARCH001 from warn to error in frob.toml [gates.severity]
    per the ticket''s own explicit instruction; frob.lock is derived-state that frob
    ack/check itself writes as a side effect of this ticket''s own work.

    '
  actor: logan
  at: '2026-07-27'
- op: add
  glob: frob.lock
  reason: 'T-0976 promotes ARCH001 from warn to error in frob.toml [gates.severity]
    per the ticket''s own explicit instruction; frob.lock is derived-state that frob
    ack/check itself writes as a side effect of this ticket''s own work.

    '
  actor: logan
  at: '2026-07-27'
evidence:
- tests/unit/test_arch.py::TestMayRaiseResolver::test_fixture_chain_own_raise_and_builtin_raiser_and_catch_subtraction
- tests/unit/test_arch.py::TestPatternRecommender::test_dataclass_boilerplate_recommends_dataclass
- tests/unit/test_arch.py::TestLayeringViolations::test_disallowed_cross_layer_edge_flagged
- tests/unit/test_arch.py::TestLockOrderingHazards::test_two_lock_ab_ba_cycle_fires_within_one_function
- tests/unit/test_arch.py::TestModuleDependencyCycles::test_two_file_import_cycle_flagged
- tests/unit/test_arch.py::TestProtocolSummaryEngine::test_leaf_function_summary_is_its_own_declarations
- tests/test_gates.py::TestPreworkSweepBounds::test_sweep_ticket_honors_graph_excludes
- tests/test_gates_fmt_directives.py::TestFormatPaths::test_check_mode_reports_without_writing
- tests/test_pii_structural_gate.py::TestFieldNames::test_password_field_fires
- tests/test_ticket_land.py::TestSpliceLedger::test_same_id_newer_state_wins
- tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork::test_archive_refuses_when_a_live_lease_exists
- tests/test_ticket_leases.py::TestSweepWorktrees::test_expired_lease_clean_removed
- tests/unit/perf/test_advisories.py::TestNestedLoopFaninAdvisories::test_hot_loop_with_multiple_callers_fires
- tests/unit/test_natives_build.py::TestNativesRunner::test_build_reports_success
- tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_adversarial_test_not_flagged
- tests/test_ticket_done_report_claims.py::TestSetDoneReportClaims::test_claims_captured_from_real_callables
- tests/unit/test_app_runners_t0976_mutation_evidence.py::TestCollectStacksViaSamplerArgvStripping::test_non_marker_first_arg_is_not_stripped
- tests/unit/test_app_runners_t0976_mutation_evidence.py::TestCollectStacksViaSamplerArgvStripping::test_marker_first_arg_is_stripped
- tests/unit/test_app_runners_t0976_mutation_evidence.py::TestCollectStacksViaSamplerArgvStripping::test_empty_argv_falls_back_to_dash_q
- tests/unit/test_app_runners_t0976_mutation_evidence.py::TestRenderDoableDispatchableByParentGrouping::test_parent_id_not_in_queue_falls_back_to_no_parent_bucket
- tests/unit/test_app_runners_t0976_mutation_evidence.py::TestRenderDoableDispatchableByParentGrouping::test_parent_id_present_in_queue_uses_its_title
- tests/unit/test_app_runners_t0976_mutation_evidence.py::TestCloseGuardsMutationEvidenceDowngrade::test_true_mutation_evidence_with_skip_flag_is_never_downgraded
- tests/unit/test_app_runners_t0976_mutation_evidence.py::TestCloseGuardsMutationEvidenceDowngrade::test_false_mutation_evidence_with_skip_flag_is_downgraded_to_none
- tests/unit/test_app_runners_t0976_mutation_evidence.py::TestCloseGuardsMutationEvidenceDowngrade::test_false_mutation_evidence_without_skip_flag_stays_false
designated_repro_test: null
threat: null
component: null
---
T-0970 landed a partial ARCH001 burn-down (5 of 52 live unwaived findings
addressed: 3 genuine refactors that dropped the function below threshold
entirely -- `_run_stamp_baseline` split into `_run_baseline_chunks`
(src/frob/app/check_runner.py), `check_layering_violations` split into
`_layering_violations_for_file` (src/frob/arch/_layering.py),
`check_no_di_construction`'s duplicated method/function loops merged into
one shared `_append_no_di_findings` helper (src/frob/arch/_layering.py) --
plus 2 honest `frob:waive ARCH001` additions for genuinely-irreducible
functions (`_check_pool_inside_pool`'s shared call-classification locals
in src/frob/arch/_concurrency.py; `_tarjan_sccs`'s indivisible iterative
Tarjan bookkeeping in src/frob/graph/summary.py) plus
`check_over_broad_except` (src/frob/arch/_fallibility.py, shared
per-catch closure) -- 3 waivers total.

This child carries the other 47 unwaived ARCH001 findings (measured via
chunked `frob check --only gates-native --json`, 2026-07-27, post-merge)
to zero unwaived: for each, either extract a real cohesive helper
(hierarchical decomposition, not mechanical line-splitting) or add an
honest `frob:waive ARCH001 reason="..."` with a real cohesion argument.
Respect existing tests: run each touched module's suite after
refactoring. Once ARCH001 is at or near zero unwaived, flip
`[gates.severity] ARCH001 = "error"` in frob.toml (T-0970's own
still-undone step -- it stayed WARN this round since 47 live findings
remain).

Live list at hand-off (file:line function, from a fresh chunked
gates-native pass):

src/frob/app/perf_runner.py:217 _collect_stacks (68 lines)
src/frob/app/ticket_runner.py:396 _doable (142 lines)
src/frob/app/ticket_runner.py:2032 _close (91 lines)
src/frob/arch/_layering.py:170 check_layering_violations -- RESOLVED in T-0970 (no longer applies; re-measure before relying on this list)
src/frob/arch/_mayraise.py:310 _own_base_raises (62 lines)
src/frob/arch/_mayraise.py:406 compute_may_raise (67 lines)
src/frob/arch/_patterns.py:1247 _check_dataclass_boilerplate (106 lines)
src/frob/arch/_patterns.py:1359 _check_manual_decorator_wrap (62 lines)
src/frob/arch/_python.py:418 _py_collect_body_events (79 lines)
src/frob/arch/_smells.py:557 check_module_dependency_cycles (67 lines)
src/frob/dup/_pipeline.py:409 _normalize_error_channel (64 lines)
src/frob/gates/__init__.py:4094 _cov006_third_file_reachable (94 lines)
src/frob/gates/__init__.py:4568 _todo003_long_deferred (76 lines)
src/frob/gates/__init__.py:4734 _fmt001_file (66 lines)
src/frob/gates/__init__.py:8094 _tick008_unknown_ledger_fields (77 lines)
src/frob/gates/_docptr.py:437 _symbol_violations (66 lines)
src/frob/gates/_fmt_directives.py:202 canonicalize_text (77 lines)
src/frob/gates/_fmt_directives.py:288 format_paths (61 lines)
src/frob/gates/_pii_structural.py:1873 pii_structural_gate (63 lines)
src/frob/gates/_prework.py:190 sweep_ticket (118 lines)
src/frob/gates/_protocol_summary.py:583 _acquiring_function_violations (102 lines)
src/frob/gates/_protocol_summary.py:746 _cleanup_always_violations (69 lines)
src/frob/gates/_protocol_summary.py:889 protocol_summary_gate (208 lines)
src/frob/graph/__init__.py:652 load_graph (85 lines)
src/frob/graph/dsl.py:229 _parse_attrs_verb_error (126 lines)
src/frob/graph/dsl.py:721 _infer_init_deinit_protocols (84 lines)
src/frob/graph/summary.py:373 compute_protocol_summaries (138 lines)
src/frob/mutate/__init__.py:309 run_mutations (94 lines)
src/frob/natives/_build.py:122 build_natives (107 lines)
src/frob/perf/_advisories.py:120 nested_loop_fanin_advisories (63 lines)
src/frob/perf/_effect_summaries.py:420 EffectGraph._summary (62 lines)
src/frob/tickets/__init__.py:226 archive (83 lines)
src/frob/tickets/__init__.py:2398 _done_transition_guard (155 lines)
src/frob/tickets/__init__.py:2598 transition (61 lines)
src/frob/tickets/__init__.py:3373 set_done_report (149 lines)
src/frob/tickets/_land.py:254 _repair_stale_land_marker (113 lines)
src/frob/tickets/_land.py:439 _newer (77 lines)
src/frob/tickets/_land.py:1862 _reverify_done_report_claims_post_merge (242 lines)
src/frob/tickets/_land.py:2726 _rewrite_draft_references_in_bodies (88 lines)
src/frob/tickets/_land.py:2824 _rewrite_draft_references_in_waive_sites (108 lines)
src/frob/tickets/_land.py:3130 _squash_and_splice_ledger (79 lines)
src/frob/tickets/_leases.py:474 read_all_leases (206 lines)
src/frob/tickets/_leases.py:800 sweep_worktrees (99 lines)
src/frob/tickets/_live_tracker.py:102 _git_grep (68 lines)
src/frob/tickets/_models.py:753 parse_claims_from_done_report (75 lines)
src/frob/tickets/_mutation_evidence.py:240 check_ticket_mutation_evidence (107 lines)

(48 lines above; one -- `check_layering_violations` -- is stale/resolved,
so 47 live. Re-measure with `frob check --only gates-native --json` at
pickup since siblings may land more fixes concurrently.)