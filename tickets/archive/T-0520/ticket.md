---
id: T-0520
title: triage residual 63 INV003/INV004 findings across 33 docs/modules+docs/strata
  files after T-0515 calibration
state: done
kind: invariant
origin: agent
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/modules/
- docs/strata/
- invariants/
- src/frob/app/telemetry.py
- src/frob/bind/__init__.py
- src/frob/clean/_core.py
- src/frob/cve/_parser.py
- src/frob/fuzz/_rules.py
- src/frob/gates/__init__.py
- src/frob/gates/_walk_lint.py
- src/frob/gates/decisions.py
- src/frob/graph/callgraph.py
- src/frob/lang/__init__.py
- src/frob/logging/filter.py
- src/frob/mutate/__init__.py
- src/frob/perf/_recursion.py
- src/frob/process/_guard.py
- src/frob/render/_color.py
- src/frob/serve/server.py
- src/frob/testing/_select.py
- src/frob/tickets/__init__.py
- src/frob/vet/_scan.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/telemetry.py
  reason: T-0520 requires binding a real frob:invariant anchor in the enforcing source
    function (INV002), not just the doc marker (INV003/INV004); each addition is a
    single-line comment, no behavior change
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/bind/__init__.py
  reason: T-0520 requires binding a real frob:invariant anchor in the enforcing source
    function (INV002), not just the doc marker (INV003/INV004); each addition is a
    single-line comment, no behavior change
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/clean/_core.py
  reason: T-0520 requires binding a real frob:invariant anchor in the enforcing source
    function (INV002), not just the doc marker (INV003/INV004); each addition is a
    single-line comment, no behavior change
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/cve/_parser.py
  reason: T-0520 requires binding a real frob:invariant anchor in the enforcing source
    function (INV002), not just the doc marker (INV003/INV004); each addition is a
    single-line comment, no behavior change
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/fuzz/_rules.py
  reason: T-0520 requires binding a real frob:invariant anchor in the enforcing source
    function (INV002), not just the doc marker (INV003/INV004); each addition is a
    single-line comment, no behavior change
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/gates/__init__.py
  reason: T-0520 requires binding a real frob:invariant anchor in the enforcing source
    function (INV002), not just the doc marker (INV003/INV004); each addition is a
    single-line comment, no behavior change
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/gates/_walk_lint.py
  reason: T-0520 requires binding a real frob:invariant anchor in the enforcing source
    function (INV002), not just the doc marker (INV003/INV004); each addition is a
    single-line comment, no behavior change
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/gates/decisions.py
  reason: T-0520 requires binding a real frob:invariant anchor in the enforcing source
    function (INV002), not just the doc marker (INV003/INV004); each addition is a
    single-line comment, no behavior change
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/graph/callgraph.py
  reason: T-0520 requires binding a real frob:invariant anchor in the enforcing source
    function (INV002), not just the doc marker (INV003/INV004); each addition is a
    single-line comment, no behavior change
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/lang/__init__.py
  reason: T-0520 requires binding a real frob:invariant anchor in the enforcing source
    function (INV002), not just the doc marker (INV003/INV004); each addition is a
    single-line comment, no behavior change
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/logging/filter.py
  reason: T-0520 requires binding a real frob:invariant anchor in the enforcing source
    function (INV002), not just the doc marker (INV003/INV004); each addition is a
    single-line comment, no behavior change
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/mutate/__init__.py
  reason: T-0520 requires binding a real frob:invariant anchor in the enforcing source
    function (INV002), not just the doc marker (INV003/INV004); each addition is a
    single-line comment, no behavior change
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/perf/_recursion.py
  reason: T-0520 requires binding a real frob:invariant anchor in the enforcing source
    function (INV002), not just the doc marker (INV003/INV004); each addition is a
    single-line comment, no behavior change
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/process/_guard.py
  reason: T-0520 requires binding a real frob:invariant anchor in the enforcing source
    function (INV002), not just the doc marker (INV003/INV004); each addition is a
    single-line comment, no behavior change
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/render/_color.py
  reason: T-0520 requires binding a real frob:invariant anchor in the enforcing source
    function (INV002), not just the doc marker (INV003/INV004); each addition is a
    single-line comment, no behavior change
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/serve/server.py
  reason: T-0520 requires binding a real frob:invariant anchor in the enforcing source
    function (INV002), not just the doc marker (INV003/INV004); each addition is a
    single-line comment, no behavior change
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/testing/_select.py
  reason: T-0520 requires binding a real frob:invariant anchor in the enforcing source
    function (INV002), not just the doc marker (INV003/INV004); each addition is a
    single-line comment, no behavior change
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/tickets/__init__.py
  reason: T-0520 requires binding a real frob:invariant anchor in the enforcing source
    function (INV002), not just the doc marker (INV003/INV004); each addition is a
    single-line comment, no behavior change
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/vet/_scan.py
  reason: T-0520 requires binding a real frob:invariant anchor in the enforcing source
    function (INV002), not just the doc marker (INV003/INV004); each addition is a
    single-line comment, no behavior change
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_walk_lint_gate.py::TestRglob::test_raw_rglob_fires
- tests/test_arch_gate.py::TestArchGateWaivers::test_ceiling_refires_when_grown_past_it
- tests/unit/test_bind.py::test_check_reports_mismatch_for_unbound_binding
- tests/test_clean.py::test_scan_skips_tracked_files
- tests/unit/cve/test_parser.py::test_parse_missing_file
- tests/test_decisions.py::test_dec002_accepted_decision_unanchored
- tests/test_gates.py::TestOptInGates::test_dup_gate_fires_on_planted_clone_when_enabled
- tests/test_fuzz.py::TestFuzz003::test_flags_stale_stamp
- tests/test_gates.py::TestCoverageGate::test_cov003_rejects_empty_directory_level_evidence
- tests/test_dup_inline.py::TestCallGraphBounds::test_public_callee_never_becomes_an_edge
- tests/test_lang.py::TestErrors::test_syntax_error_yields_partial_symbols
- tests/unit/test_logging_module.py::test_below_level_filter
- tests/test_mutate.py::test_run_mutations_survivors_when_tests_weak
- tests/test_perf.py::test_perf005_fires_on_unproven_self_recursion
- tests/unit/test_process_guard.py::TestGuardedSubprocessRun::test_disabled_returns_err_without_spawning
- tests/unit/test_render.py::TestResolveColor::test_no_color_flag_wins_over_everything
- tests/test_serve.py::TestBuildServer::test_registers_all_five_tools
- tests/test_telemetry.py::test_redact_command_hides_recognizable_secret
- tests/test_testing.py::TestSelect::test_reversed_directive_never_selects_the_source_symbol
- tests/test_tickets_lease.py::TestDoable::test_real_collision_is_hidden_from_default_doable
- tests/test_vet.py::TestObfuscationEnsemble::test_scan_directory_obfuscation_finds_signal_in_one_file
- tests/unit/strata/test_selfconform.py::TestStaleDesign::test_stale_design_skips_node_fully_within_graph_exclude
- tests/unit/strata/test_crash.py::TestNoHangCheck::test_missing_timeout_into_crashable_node_fails_closed
- tests/unit/strata/test_facts.py::TestClosure::test_worst_age_reports_unbounded_on_a_positive_cycle
- tests/unit/strata/test_threat.py::TestDischargeCompleteness::test_discharge_claim_below_required_rung_is_a_violation
- tests/unit/strata/test_policy.py::TestScopeResolution::test_trust_scope_resolves_via_lattice
- tests/unit/strata/test_krb.py::TestKrbTrustFlows::test_two_way_synthesizes_reverse_edge_too
- tests/test_tickets.py::TestDoable::test_blocked_excluded
- tests/unit/strata/test_host_isolation.py::TestVerticalIsolation::test_sudoers_does_not_fire_when_undeclared
- tests/unit/strata/test_elaborate.py::TestElaborateValidation::test_duplicate_node_id_fails_closed
- tests/unit/strata/test_threat.py::TestCatalogCompleteness::test_missing_entry_is_a_violation
- tests/unit/strata/test_litmus_waive.py::TestWaiveLitmus::test_sub_target_waiver_does_not_suppress_a_different_sub_target
designated_repro_test: null
threat: null
component: null
---
T-0515 calibrated INV003/INV004: INV004 changed from per-section to per-file granularity and scoped to INV003_SPEC_DIRS (docs/modules, docs/strata), matching INV003's own T-0509 rationale. Combined INV003+INV004 dropped from 604 to 63 (INV003 unchanged at 30, INV004 573 -> 33), measured via frob check --only invariant on this worktree before/after -- see docs/modules/gates.md's INV004 section for the full before/after story. The residual 63 findings span exactly 33 files (each file usually carries both an INV003 and an INV004 hit): docs/modules/{vet,fuzz,serve,dup,clean,render,lang,testing,dup-sota-survey,process,arch,logging,decisions,graph,cve,stats,tickets,perf,bind,app,mutate}.md and docs/strata/{kernel,evidence,policy,boundary,selfconform,roadmap,krb,waive,charter,host,surface,threat}.md. None of docs/modules or docs/strata currently binds a single real invariants/INV-###.md entry -- this is genuine, not a calibration artifact. Triage each file: bind a real invariants/INV-###.md entry where the claim is mechanically checkable (a test or policy rule already proves it), reword where the doc overclaims beyond what is enforced, or markdown-waive with a specific per-file reason (<!-- frob:waive INV003|INV004 reason="..." -->) where the claim is true design intent but not provable. Batch by file, do not blanket-waive. Get the exact remaining count from frob check --only invariant --json.