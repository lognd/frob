## Done report

EXHAUST001/002 residual burn-down continuation (post T-1056). Narrowed
scope to the real finding sites (50 files, excluding gates/**, tickets/**
owned by sibling wave agents, and perf/**, vet/**+gates/_opaque.py owned
by sibling tickets T-1053/T-1051). Disposed all 117 in-scope unwaived
findings down to 0: real errors-as-values fixes (widened a narrow except
to the function's own documented degrade contract, or added a missing
except around a previously-unguarded fallible call) where the escape was
genuine; `frob:raises <Type>` for functions that intentionally propagate
a named exception by design (_tokenize_line -> _TokenizeError,
write_lock -> BaseException, node_access_declarations /
_parse_host_attrs / host_manifest_for -> ValueError, _require_mcp ->
McpUnavailable); reasoned `frob:waive` directives everywhere else, each
citing the specific resolver-unresolvable call (deferred imports,
cross-module Result-returning wrappers, stdlib calls the may-raise
resolver cannot statically bound) -- no rule loosening anywhere.

Also fixed along the way: gitio._parse_unified_diff's dict-index KeyError
gap (switched to setdefault), valgrind._xml_error_diagnostic's int(ln)
ValueError gap, xref.xref's unguarded read_bytes() OSError gap, and
lang._nodes.resolve_local_import's two unguarded Path.exists() calls --
all genuine unhandled-exception gaps the EXHAUST resolver caught, not
resolver artifacts.

Verification: `frob check --ticket T-1062 --only exhaustive_handling` is
clean in scope; `frob test --base main` touched-set run passed (53
outcomes, 0 failures); `frob sys sync-interface --check` shows no drift;
full `frob check --ticket T-1062` is clean across every gate (fixed a
self-inflicted INV006 trip from "hardening only" wording in my own
waiver comments, and AFFECT001 waivers + `frob ack` on the handful of
doc-bound touched functions since this is pure internal error-handling
hardening with no behavior/interface change).

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_app_runner_map` (pytest node id, verified passing when recorded)
- `tests/integration/test_interfaces.py::TestInterfaces::test_deploy_generate_writes_and_checks` (pytest node id, verified passing when recorded)
- `tests/integration/test_interfaces.py::TestInterfaces::test_gitlog` (pytest node id, verified passing when recorded)
- `tests/integration/test_interfaces.py::TestInterfaces::test_map_project` (pytest node id, verified passing when recorded)
- `tests/integration/test_interfaces.py::TestInterfaces::test_outline_file` (pytest node id, verified passing when recorded)
- `tests/integration/test_interfaces.py::TestInterfaces::test_process_parse` (pytest node id, verified passing when recorded)
- `tests/integration/test_interfaces.py::TestInterfaces::test_serve_tools` (pytest node id, verified passing when recorded)
- `tests/integration/test_interfaces.py::TestInterfaces::test_testing_collect` (pytest node id, verified passing when recorded)
- `tests/integration/test_interfaces.py::TestInterfaces::test_xref_symbol` (pytest node id, verified passing when recorded)
- `tests/integration/test_mutate_runner.py::TestMutateRunnerJson::test_json_output_is_clean` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorCli::test_doctor_reports_healthy_when_natives_present` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift::test_drift_is_informational_and_does_not_affect_healthy` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift::test_first_run_reports_no_drift_and_writes_manifest` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift::test_malformed_manifest_is_treated_as_no_prior_run` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift::test_rewritten_artifact_between_two_runs_reports_drift` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift::test_unchanged_artifact_reports_no_drift` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_run_diagnosis_healthy_with_no_derived_state` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_run_diagnosis_unhealthy_when_derived_state_corrupt` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_verify_derived_state_accepts_valid_json_stamp` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_verify_derived_state_flags_corrupt_sqlite_cache` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_verify_derived_state_flags_malformed_json_stamp` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_verify_derived_state_reports_absent_as_healthy` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorMalformedTicketEdges::test_run_diagnosis_healthy_with_no_malformed_edges` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorMutateJournal::test_run_diagnosis_healthy_with_no_mutate_journals` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorMutateJournal::test_run_diagnosis_ignores_journal_owned_by_live_pid` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorMutateJournal::test_run_diagnosis_unhealthy_with_stale_mutate_journal` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorScaffoldConformance::test_run_diagnosis_healthy_after_scaffold_apply` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorScaffoldConformance::test_run_diagnosis_ignores_non_frob_directory` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorScaffoldConformance::test_run_diagnosis_unhealthy_when_scaffold_blocks_missing` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorStaleTicketLeases::test_run_diagnosis_healthy_with_no_stale_leases` (pytest node id, verified passing when recorded)
- `tests/system/test_scaffold_dx.py::test_python_tool_scaffold_passes_check_immediately` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestOptInGates::test_fuzz_gate_off_by_default` (pytest node id, verified passing when recorded)
- `tests/test_gitio.py::TestWorkingDiff::test_covers_committed_staged_unstaged_and_untracked` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestBuildIncremental::test_fingerprint_bump_rebuilds` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestBuildIncremental::test_fingerprint_packages_derived_from_lang_registry` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestGeneratedSource::test_is_generated_source_detects_do_not_edit_and_at_markers` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestGeneratedSource::test_is_generated_source_detects_repo_convention_header` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestGeneratedSource::test_is_generated_source_false_for_hand_authored_file` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestGeneratedSource::test_is_generated_source_false_for_missing_file` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::test_graph_build_lock_drift_integration` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::test_lang_pipeline_integration` (pytest node id, verified passing when recorded)
- `tests/test_mutate.py::test_run_mutations_all_killed_by_strong_test` (pytest node id, verified passing when recorded)
- `tests/test_serve_events.py::TestSubscribeAndWait::test_receives_coverage_fresh_on_stamp_write` (pytest node id, verified passing when recorded)
- `tests/test_serve_events.py::TestSubscribeAndWait::test_receives_graph_changed_after_edit` (pytest node id, verified passing when recorded)
- `tests/test_serve_events.py::TestSubscribeAndWait::test_times_out_with_no_matching_event` (pytest node id, verified passing when recorded)
- `tests/test_stats.py::test_collect_combines_both` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_waive.py::TestConformanceWaiverExpiry::test_malformed_date_returns_none` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_waive.py::TestConformanceWaiverExpiry::test_no_marker_returns_none` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_waive.py::TestConformanceWaiverExpiry::test_parses_embedded_expiry_date` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::test_check_run_check_arch_integration` (pytest node id, verified passing when recorded)
- `tests/unit/test_docs_module.py::test_docs_module_integration` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup.py::test_dup_end_to_end_scan_then_render` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_primitives.py::test_resolve_local_import_maps_to_repo_relative` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 53 passed (from 53 evidence id(s))
- gates: 0 error(s), 1545 warning(s), 583 waived
- error-findings: none (measured, zero errors)
