---
id: T-1062
title: EXHAUST001/002 residual burn-down continuation (post T-1056)
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/check_runner.py
- src/frob/app/config.py
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/app/ticket_runner/_mutate.py
- src/frob/check/_python.py
- src/frob/check/_ts.py
- src/frob/deploy/_conform.py
- src/frob/docs/__init__.py
- src/frob/doctor.py
- src/frob/dup/_pipeline/_probe.py
- src/frob/dup/_pipeline/_smt.py
- src/frob/fuzz/_signatures.py
- src/frob/gitio.py
- src/frob/gitlog/__init__.py
- src/frob/graph/_generated.py
- src/frob/graph/cache.py
- src/frob/graph/lock.py
- src/frob/lang/__init__.py
- src/frob/lang/_nodes.py
- src/frob/map/__init__.py
- src/frob/mutate/__init__.py
- src/frob/mutate/_journal.py
- src/frob/natives/_build.py
- src/frob/outline/__init__.py
- src/frob/process/parsers/cargo.py
- src/frob/process/parsers/valgrind.py
- src/frob/scaffold/_managed.py
- src/frob/scaffold/project.py
- src/frob/serve/_events.py
- src/frob/serve/_socketd.py
- src/frob/serve/_warm.py
- src/frob/serve/server.py
- src/frob/stats/_agentic.py
- src/frob/strata/_access.py
- src/frob/strata/_claims.py
- src/frob/strata/_code_binding.py
- src/frob/strata/_compliance.py
- src/frob/strata/_elaborate.py
- src/frob/strata/_facts.py
- src/frob/strata/_host.py
- src/frob/strata/_host_isolation.py
- src/frob/strata/_mode_conformance.py
- src/frob/strata/_native_staleness.py
- src/frob/strata/_obligation_proof.py
- src/frob/strata/_reliability.py
- src/frob/strata/_waive.py
- src/frob/testing/_collect.py
- src/frob/testing/_coverage_wait.py
- src/frob/testing/_runners.py
- src/frob/xref/__init__.py
- frob.lock
- src/frob/testing/_collect_cpp.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/app/check_runner.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/app/config.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/app/ticket_runner/_close_cmd.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/app/ticket_runner/_mutate.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/check/_python.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/check/_ts.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/deploy/_conform.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/docs/__init__.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/doctor.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/dup/_pipeline/_probe.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/dup/_pipeline/_smt.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/fuzz/_signatures.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/gitio.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/gitlog/__init__.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/graph/_generated.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/graph/cache.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/graph/lock.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/lang/__init__.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/lang/_nodes.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/map/__init__.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/mutate/__init__.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/mutate/_journal.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/natives/_build.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/outline/__init__.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/process/parsers/cargo.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/process/parsers/valgrind.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/scaffold/_managed.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/scaffold/project.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/serve/_events.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/serve/_socketd.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/serve/_warm.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/serve/server.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/stats/_agentic.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/strata/_access.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/strata/_claims.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/strata/_code_binding.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/strata/_compliance.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/strata/_elaborate.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/strata/_facts.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/strata/_host.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/strata/_host_isolation.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/strata/_mode_conformance.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/strata/_native_staleness.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/strata/_obligation_proof.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/strata/_reliability.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/strata/_waive.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/testing/_collect.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/testing/_coverage_wait.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/testing/_runners.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/xref/__init__.py
  reason: narrow to real EXHAUST001/002 finding sites, excluding gates/** tickets/**
    perf/** vet/** owned by sibling agents this wave
  actor: logan
  at: '2026-07-29'
- op: add
  glob: frob.lock
  reason: frob ack writes doc-facet digests to frob.lock; needed to satisfy AFFECT001
    acks for T-1062's touched functions
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/testing/_collect_cpp.py
  reason: T-1074 landed a split of testing/_collect.py mid-wave; the two EXHAUST001
    sites this ticket fixed there moved to _collect_cpp.py, reapplied on merge
  actor: logan
  at: '2026-07-29'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_app_runner_map
- tests/integration/test_interfaces.py::TestInterfaces::test_deploy_generate_writes_and_checks
- tests/integration/test_interfaces.py::TestInterfaces::test_gitlog
- tests/integration/test_interfaces.py::TestInterfaces::test_map_project
- tests/integration/test_interfaces.py::TestInterfaces::test_outline_file
- tests/integration/test_interfaces.py::TestInterfaces::test_process_parse
- tests/integration/test_interfaces.py::TestInterfaces::test_serve_tools
- tests/integration/test_interfaces.py::TestInterfaces::test_testing_collect
- tests/integration/test_interfaces.py::TestInterfaces::test_xref_symbol
- tests/integration/test_mutate_runner.py::TestMutateRunnerJson::test_json_output_is_clean
- tests/system/test_cli_doctor.py::TestDoctorCli::test_doctor_reports_healthy_when_natives_present
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift::test_drift_is_informational_and_does_not_affect_healthy
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift::test_first_run_reports_no_drift_and_writes_manifest
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift::test_malformed_manifest_is_treated_as_no_prior_run
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift::test_rewritten_artifact_between_two_runs_reports_drift
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift::test_unchanged_artifact_reports_no_drift
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_run_diagnosis_healthy_with_no_derived_state
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_run_diagnosis_unhealthy_when_derived_state_corrupt
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_verify_derived_state_accepts_valid_json_stamp
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_verify_derived_state_flags_corrupt_sqlite_cache
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_verify_derived_state_flags_malformed_json_stamp
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_verify_derived_state_reports_absent_as_healthy
- tests/system/test_cli_doctor.py::TestDoctorMalformedTicketEdges::test_run_diagnosis_healthy_with_no_malformed_edges
- tests/system/test_cli_doctor.py::TestDoctorMutateJournal::test_run_diagnosis_healthy_with_no_mutate_journals
- tests/system/test_cli_doctor.py::TestDoctorMutateJournal::test_run_diagnosis_ignores_journal_owned_by_live_pid
- tests/system/test_cli_doctor.py::TestDoctorMutateJournal::test_run_diagnosis_unhealthy_with_stale_mutate_journal
- tests/system/test_cli_doctor.py::TestDoctorScaffoldConformance::test_run_diagnosis_healthy_after_scaffold_apply
- tests/system/test_cli_doctor.py::TestDoctorScaffoldConformance::test_run_diagnosis_ignores_non_frob_directory
- tests/system/test_cli_doctor.py::TestDoctorScaffoldConformance::test_run_diagnosis_unhealthy_when_scaffold_blocks_missing
- tests/system/test_cli_doctor.py::TestDoctorStaleTicketLeases::test_run_diagnosis_healthy_with_no_stale_leases
- tests/system/test_scaffold_dx.py::test_python_tool_scaffold_passes_check_immediately
- tests/test_gates.py::TestOptInGates::test_fuzz_gate_off_by_default
- tests/test_gitio.py::TestWorkingDiff::test_covers_committed_staged_unstaged_and_untracked
- tests/test_graph.py::TestBuildIncremental::test_fingerprint_bump_rebuilds
- tests/test_graph.py::TestBuildIncremental::test_fingerprint_packages_derived_from_lang_registry
- tests/test_graph.py::TestGeneratedSource::test_is_generated_source_detects_do_not_edit_and_at_markers
- tests/test_graph.py::TestGeneratedSource::test_is_generated_source_detects_repo_convention_header
- tests/test_graph.py::TestGeneratedSource::test_is_generated_source_false_for_hand_authored_file
- tests/test_graph.py::TestGeneratedSource::test_is_generated_source_false_for_missing_file
- tests/test_graph.py::test_graph_build_lock_drift_integration
- tests/test_lang.py::test_lang_pipeline_integration
- tests/test_mutate.py::test_run_mutations_all_killed_by_strong_test
- tests/test_serve_events.py::TestSubscribeAndWait::test_receives_coverage_fresh_on_stamp_write
- tests/test_serve_events.py::TestSubscribeAndWait::test_receives_graph_changed_after_edit
- tests/test_serve_events.py::TestSubscribeAndWait::test_times_out_with_no_matching_event
- tests/test_stats.py::test_collect_combines_both
- tests/unit/strata/test_waive.py::TestConformanceWaiverExpiry::test_malformed_date_returns_none
- tests/unit/strata/test_waive.py::TestConformanceWaiverExpiry::test_no_marker_returns_none
- tests/unit/strata/test_waive.py::TestConformanceWaiverExpiry::test_parses_embedded_expiry_date
- tests/unit/test_check.py::test_check_run_check_arch_integration
- tests/unit/test_docs_module.py::test_docs_module_integration
- tests/unit/test_dup.py::test_dup_end_to_end_scan_then_render
- tests/unit/test_lang_primitives.py::test_resolve_local_import_maps_to_repo_relative
designated_repro_test: null
threat: null
component: null
---
Follow-up to T-1056, which closed only the src/frob/gates/__init__.py
slice (16 of 176 sites) of the EXHAUST001/002 turn-on debt burn-down.

Remaining sites (per T-1056's `frob check --only exhaustive_handling
--json` snapshot, minus the closed gates/__init__.py slice and minus the
two sibling-owned trees T-1056 skipped for coordination):

  8 src/frob/gates/_coverage.py
  6 src/frob/dup/_pipeline.py
  6 src/frob/tickets/_leases.py
  5 src/frob/deploy/_conform.py
  5 src/frob/mutate/__init__.py
  5 src/frob/outline/__init__.py
  5 src/frob/strata/_claims.py
  5 src/frob/tickets/__init__.py
  4 src/frob/app/check_runner.py
  4 src/frob/check/_python.py
  4 src/frob/gates/_docptr.py
  4 src/frob/gates/_secrets.py
  4 src/frob/mutate/_journal.py
  4 src/frob/strata/_host_isolation.py
  4 src/frob/strata/_native_staleness.py
  4 src/frob/testing/_collect.py
  3 src/frob/doctor.py
  3 src/frob/gates/_docblocks.py
  3 src/frob/gates/_prework.py
  3 src/frob/stats/_agentic.py
  3 src/frob/xref/__init__.py
  ...remainder spread 1-2 per file across app/gates/check/strata/testing.

Excluded from this list entirely (owned by sibling tickets, do not
recount without checking their status first): src/frob/perf/** (T-1053)
and src/frob/vet/** plus src/frob/gates/_opaque.py (T-1051).

Same disposition rule as T-1056/T-1022: each site gets a truthful
frob:raises/frob:callee-raises annotation (verify against what the
callable can actually raise), a cheap errors-as-values refactor
(tool_crash_result()-style at subprocess/parse boundaries, or a fail-open
try/except matching the function's own documented degrade contract), or a
reasoned frob:waive -- never a blanket suppression. Re-run
`frob check --only exhaustive_handling --json` at the start to get a live
count before starting (T-1056's counts will have drifted).