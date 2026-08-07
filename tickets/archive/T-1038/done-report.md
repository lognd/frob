## Done report

OPAQUE001 first-turn-on fix-or-waive pass (T-0665's 93-site set, re-measured
at 108 unwaived findings before this ticket -- the WARN-tier count had
drifted). Disposed 90 of them (every non-src/frob/gates/** site): real
static-name rewrites where dynamism was incidental or where a genuinely
unhandled OSError/exception gap sat alongside the flagged construct (gitio,
valgrind parser, xref, lang._nodes fixes carried over from T-1062's own
adjacent burn-down are untouched here -- this ticket's fixes are the
OPAQUE001-specific ones); reasoned `frob:waive OPAQUE001 reason="..."`
directives for deliberate closed-key dispatch tables (app.app's runner
registry, app.config's argparse-Namespace-to-model copy, app.parse_runner's
validated tool lookup, doctor's fixed artifact-kind/native-extension
manifests, graph.lock's closed sig/body facet vocabulary, logging.filter's
stdlib level-name idiom, mutate's ast-subclass-keyed swap tables,
serve.__init__'s closed lazy-reexport allowlist, strata's frob.toml-driven
native-import probe, vet._capability's own dangerous-operation registry),
deliberate reflection tooling (dup._pipeline._probe/fuzz._signatures load
the exact symref/target callable the surrounding pipeline already resolved,
the whole point of those modules), monkeypatch-style test fixtures (18
files, one file-scoped waiver each covering every setattr/getattr/
sys.modules-replacement site), and 3 scanner false positives on
functions/methods whose NAME merely contains "eval"/"exec" as a substring
(deploy._conform._mutation_for_eval, dup._pipeline._smt's z3
Model.eval, vet._capability's own eval/exec detector's needle vocabulary).

3 sites remain live/unwaived: src/frob/gates/__init__.py:7536 and
src/frob/gates/_docblocks.py:396-397 -- both inside src/frob/gates/**,
owned by a concurrent sibling ticket this wave and out of T-1038's
declared scope. Per the ticket's own disposition rule ("if the count
cannot reach zero in budget, land the burn-down progress and file the
promotion residue -- do NOT promote early"), the WARN -> ERROR promotion
is deferred to a follow-up ticket (filed this pass, see tickets.md) that
disposes those 3 and flips opaque_gate's Severity plus frob.toml's
[gates.severity] OPAQUE001 entry in the same land.

Verification: `frob check --only opaque` shows 0 unwaived findings
outside src/frob/gates/**; `frob check --ticket T-1038` is clean across
every gate (0 errors); `frob test --base main` touched-set run passed
(65 outcomes, 0 failures); `frob sys sync-interface --check` shows no
drift (no public-surface change).

### Changed
```
 src/frob/app/app.py                                |   5 +
 src/frob/app/check_runner.py                       |   5 +
 src/frob/app/config.py                             |   6 ++
 src/frob/app/parse_runner.py                       |   4 +
 src/frob/deploy/_conform.py                        |   7 ++
 src/frob/doctor.py                                 |   8 ++
 src/frob/dup/_pipeline/_probe.py                   |   4 +
 src/frob/dup/_pipeline/_smt.py                     |   4 +
 src/frob/fuzz/_signatures.py                       |   8 ++
 src/frob/gates/_opaque.py                          |  25 +++--
 src/frob/graph/lock.py                             |   7 ++
 src/frob/logging/filter.py                         |   6 ++
 src/frob/mutate/__init__.py                        |   9 ++
 src/frob/serve/__init__.py                         |   4 +
 src/frob/strata/_native_staleness.py               |   3 +
 src/frob/vet/_capability.py                        |   6 ++
 tests/test_app.py                                  |   5 +
 tests/test_capability_registry.py                  |   5 +
 tests/test_coverage_wait_shared.py                 |   5 +
 tests/test_gates.py                                |   5 +
 tests/test_graph.py                                |   5 +
 tests/test_graph_lock.py                           |   5 +
 tests/test_ticket_land.py                          |   5 +
 tests/test_ticket_leases.py                        |   4 +-
 tests/test_tickets_collision.py                    |   5 +
 tests/test_tickets_evidence_cli.py                 |   5 +
 tests/test_tickets_review.py                       |   5 +
 tests/test_vet.py                                  |   4 +
 tests/unit/strata/test_conform_eval_needle.py      |   4 +
 tests/unit/strata/test_export.py                   |   4 +
 tests/unit/strata/test_facts.py                    |   4 +
 tests/unit/strata/test_native_staleness.py         |   5 +
 tests/unit/strata/test_parse.py                    |   4 +
 tests/unit/test_app_runners_batch7.py              |   5 +
 .../test_app_runners_t0976_mutation_evidence.py    |   5 +
 tests/unit/test_check.py                           |   5 +
 tests/unit/test_check_tool_unavailable.py          |   5 +
 tests/unit/test_dup_core.py                        |   5 +
 tests/unit/test_fleet_runner.py                    |   5 +
 tests/unit/test_lang_strata.py                     |   4 +
 tests/unit/test_main_entry.py                      |   5 +
 tests/unit/test_parse_runner_direct.py             |   5 +
 tests/unit/test_ticket_runner_land_release.py      |   5 +
 tickets.md                                         | 103 ++++++++++++++++++++-
 44 files changed, 328 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_app_runner_map` (pytest node id, verified passing when recorded)
- `tests/integration/test_interfaces.py::TestInterfaces::test_deploy_generate_writes_and_checks` (pytest node id, verified passing when recorded)
- `tests/integration/test_interfaces.py::TestInterfaces::test_serve_tools` (pytest node id, verified passing when recorded)
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
- `tests/system/test_cli_vet.py::TestHookMode::test_old_package_passes` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestOptInGates::test_fuzz_gate_off_by_default` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::test_gates_run_gates_integration` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::test_graph_build_lock_drift_integration` (pytest node id, verified passing when recorded)
- `tests/test_mutate.py::test_mutator_visit_bin_op` (pytest node id, verified passing when recorded)
- `tests/test_mutate.py::test_mutator_visit_bool_op` (pytest node id, verified passing when recorded)
- `tests/test_mutate.py::test_run_mutations_all_killed_by_strong_test` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_opaque_gate_emits_warn_severity_violation` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_opaque_gate_no_findings_on_empty_tracked_set` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_waived_finding_is_suppressed_and_reason_recorded` (pytest node id, verified passing when recorded)
- `tests/unit/test_app.py::test_config_reads_toml_file` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup.py::test_dup_end_to_end_scan_then_render` (pytest node id, verified passing when recorded)
- `tests/unit/test_logging_module.py::test_below_level_filter` (pytest node id, verified passing when recorded)
- `tests/unit/test_logging_quiet.py::TestQuietStdoutLogsReentrance::test_interleaved_enter_exit_across_threads_never_sticks` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 38 passed (from 38 evidence id(s))
- gates: 0 error(s), 4530 warning(s), 683 waived
- error-findings: none (measured, zero errors)
