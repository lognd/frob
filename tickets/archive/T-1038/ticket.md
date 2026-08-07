---
id: T-1038
title: promote OPAQUE001 to ERROR-tier once frob's own 93-site first-turn-on set is
  fixed-or-waived
state: done
kind: security
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_opaque.py
- src/frob/vet/**
- src/frob/app/config.py
- src/frob/deploy/**
- src/frob/dup/**
- src/frob/fuzz/**
- src/frob/graph/**
- tests/**
- src/frob/app/app.py
- src/frob/app/check_runner.py
- src/frob/app/parse_runner.py
- src/frob/doctor.py
- src/frob/logging/filter.py
- src/frob/mutate/__init__.py
- src/frob/serve/__init__.py
- src/frob/strata/_native_staleness.py
- frob.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: frob.toml
  reason: promoting OPAQUE001 to ERROR tier requires the [gates.severity] table entry,
    same land as the code-level Severity.ERROR change and the zero-unwaived-count
    burn-down
  actor: logan
  at: '2026-07-29'
- op: remove
  glob: frob.toml
  reason: reverted the OPAQUE001 promotion (3 gates/** sites out of scope remain unwaived
    repo-wide) -- promotion deferred to a follow-up ticket, no longer touching frob.toml
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/app/app.py
  reason: OPAQUE001 fix-or-waive pass surfaced real sites in these production files
    too, not only the ticket's originally-declared scope
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/app/check_runner.py
  reason: OPAQUE001 fix-or-waive pass surfaced real sites in these production files
    too, not only the ticket's originally-declared scope
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/app/parse_runner.py
  reason: OPAQUE001 fix-or-waive pass surfaced real sites in these production files
    too, not only the ticket's originally-declared scope
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/doctor.py
  reason: OPAQUE001 fix-or-waive pass surfaced real sites in these production files
    too, not only the ticket's originally-declared scope
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/logging/filter.py
  reason: OPAQUE001 fix-or-waive pass surfaced real sites in these production files
    too, not only the ticket's originally-declared scope
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/mutate/__init__.py
  reason: OPAQUE001 fix-or-waive pass surfaced real sites in these production files
    too, not only the ticket's originally-declared scope
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/serve/__init__.py
  reason: OPAQUE001 fix-or-waive pass surfaced real sites in these production files
    too, not only the ticket's originally-declared scope
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/strata/_native_staleness.py
  reason: OPAQUE001 fix-or-waive pass surfaced real sites in these production files
    too, not only the ticket's originally-declared scope
  actor: logan
  at: '2026-07-29'
- op: add
  glob: frob.lock
  reason: frob ack writes doc-facet digests to frob.lock for the 4 touched functions
    carrying frob:doc bindings
  actor: logan
  at: '2026-07-29'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_app_runner_map
- tests/integration/test_interfaces.py::TestInterfaces::test_deploy_generate_writes_and_checks
- tests/integration/test_interfaces.py::TestInterfaces::test_serve_tools
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
- tests/system/test_cli_vet.py::TestHookMode::test_old_package_passes
- tests/test_gates.py::TestOptInGates::test_fuzz_gate_off_by_default
- tests/test_gates.py::test_gates_run_gates_integration
- tests/test_graph.py::test_graph_build_lock_drift_integration
- tests/test_mutate.py::test_mutator_visit_bin_op
- tests/test_mutate.py::test_mutator_visit_bool_op
- tests/test_mutate.py::test_run_mutations_all_killed_by_strong_test
- tests/test_vet.py::TestOpaqueIndirectionGate::test_opaque_gate_emits_warn_severity_violation
- tests/test_vet.py::TestOpaqueIndirectionGate::test_opaque_gate_no_findings_on_empty_tracked_set
- tests/test_vet.py::TestOpaqueIndirectionGate::test_waived_finding_is_suppressed_and_reason_recorded
- tests/unit/test_app.py::test_config_reads_toml_file
- tests/unit/test_dup.py::test_dup_end_to_end_scan_then_render
- tests/unit/test_logging_module.py::test_below_level_filter
- tests/unit/test_logging_quiet.py::TestQuietStdoutLogsReentrance::test_interleaved_enter_exit_across_threads_never_sticks
designated_repro_test: null
threat: null
component: null
---
T-0665 landed OPAQUE001 (frob.gates._opaque.opaque_gate) at WARN-tier
per the T-0688/T-0973 first-turn-on promotion precedent: a first
measurement against frob's own tracked codebase found 93 real sites
after string-literal/comment false-positive filtering (147 before),
concentrated in test fixtures using dynamic getattr/setattr for
monkeypatch-style assertions, plus a handful of production sites
(src/frob/app/config.py, src/frob/deploy/_conform.py,
src/frob/dup/_pipeline.py, src/frob/fuzz/_signatures.py,
src/frob/graph/lock.py, src/frob/vet/_capability.py itself). This is
above the >25-site WARN-first threshold, so promoting straight to
ERROR was not safe to do in the same ticket.

Scope: audit each of the ~93 sites and either (a) rewrite to a static
name where the dynamic lookup was incidental, or (b) add an honest
`frob:waive OPAQUE001 reason="..."` naming why the site is a legitimate
runtime-resolved indirection (most test-fixture sites will fall here --
mock/monkeypatch dynamic attribute access is often intentional test
infrastructure, not an evasion risk). Once the WARN count reaches zero
real (unwaived) findings, promote opaque_gate's Severity from WARN to
ERROR in src/frob/gates/_opaque.py.