## Done report

Changed (13 files, format-only, ruff format via `frob format` per-file):
tests/system/test_cli_ticket.py
tests/system/test_cli_ticket_promote.py
tests/system/test_fleet_status_ticket_readiness_arch001.py
tests/system/test_frob_self_model.py
tests/test_gates.py
tests/test_gates_fmt_directives.py
tests/test_graph.py
tests/test_lang.py
tests/test_tick013_gate.py
tests/test_ticket_evidence.py
tests/test_ticket_leases.py
tests/test_ticket_reconcile.py
tests/test_tickets.py

File-selection note: this batch was picked from the 72 files
`ruff format --check .` reported remaining after batch 10, MINUS every
file already claimed by T-draft-8e8177c3's live cross-worktree lease
(T-2373's empty-scope epic rollup child, currently holding tests/conftest.py,
test_ticket_land.py, test_ticket_land_proof_claims.py,
test_ticket_work_and_land_finish.py, test_tickets_acceptance.py,
test_tickets_lease.py, test_tickets_organization.py, test_tickets_priority.py,
unit/strata/test_selfconform.py, unit/test_app_runners_batch6.py,
unit/test_app_runners_json_guard_t2492.py,
unit/test_app_runners_t2395_contention.py) -- `frob ticket start` refused
twice on a lease collision before this exact set was reached (tests/conftest.py,
then tests/test_ticket_land.py), each swapped for the next unclaimed file
in the remaining list rather than forced through. T-2790 (docs/investigations/)
and T-2793 (rapid_sweep/verify/gate_findings/tickets-landing.md) were also
checked and had no overlap with this batch.

Diff reviewed by hand: every file's diff is pure line-wrap/import-order
reformatting (spot-checked test_ticket_leases.py, test_lang.py, test_graph.py
directly) -- no logic touched, no fixture-corpus file in the diff.
`frob format` needed zero ruff-check-fix autofixes on any of the 13 files,
only ruff-format-write.

Evidence: 13 pytest node ids bound, one per touched file, all pass.

Pre-existing failures (reproduced identically on unmodified main at the
primary checkout /home/logan/projects/frob, BEFORE this diff existed there
-- confirmed by running the exact same node ids there first), not caused
by this reformat:
- tests/system/test_cli_ticket.py::TestTicketRoundTrip::test_start_auto_plans_queued_ticket
- tests/system/test_cli_ticket.py::TestTicketRoundTrip::test_plan_then_sweep_flow
- tests/system/test_cli_ticket.py::TestTicketRoundTrip::test_close_with_evidence_and_done_report_succeeds
- tests/system/test_cli_ticket.py::TestTicketRoundTrip::test_close_without_evidence_fails
- tests/system/test_cli_ticket_promote.py::TestPromoteCLI::test_promotes_a_draft_carrying_evidence_and_done_report
- tests/test_gates.py::TestWireGate::test_new_cli_dest_present_in_config_external_is_not_flagged
- tests/test_gates.py::TestFixEngineTierABatch2::test_docenum001_fails_before_fix_and_passes_after
- tests/test_gates.py::TestAutofixManifest::test_killed_mid_handler_leaves_manifest_naming_completed_fixes
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations (SYS003 undeclared cross-component import findings, unrelated to this diff)
- tests/test_ticket_evidence.py::TestEvidenceCmdCwd::test_relative_probe_only_succeeds_from_worktree
- tests/test_ticket_leases.py::TestCommitFullLedgerChange::test_archive_cli_leaves_repo_clean
- tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_dispatch_table_verbs_are_all_accounted_for
- tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_verb_leaves_repo_clean[component/priority/kind/tier]

An initial xdist run under heavy fleet load (LOAD 16.1) hit an
INTERNALERROR scheduler crash (KeyError on a WorkerController) that
manufactured a few extra false failures (test_checker_fleet_deploy_vet_have_no_undeclared_fs_write_selfaudit001,
test_ticket_readiness_is_not_an_arch001_finding, test_fragments_module_fs_read_is_declared_not_selfaudit001)
-- re-run individually with -n 0 / -n 2, all three pass cleanly and are
excluded from the pre-existing list above.

Full clean groups confirmed with 0 failures: tests/test_graph.py,
tests/test_tickets.py, tests/test_lang.py, tests/test_tick013_gate.py,
tests/test_ticket_reconcile.py, tests/test_gates_fmt_directives.py (479
collected, 0 failed).

Filed: this is child batch 11 of T-2359 (parent epic-tracking ticket,
still open pending further batches; 72 -> 59 files remaining after this
batch).

Gates: `frob format` applied ruff-format-write only (no autofixes) per
file; diff reviewed by hand, no semantic changes.

### Changed
```
 rapid-debt.jsonl                                   |   2 +
 tests/system/test_cli_ticket.py                    |  18 +++-
 tests/system/test_cli_ticket_promote.py            |  13 ++-
 .../test_fleet_status_ticket_readiness_arch001.py  |   3 +-
 tests/system/test_frob_self_model.py               |   8 +-
 tests/test_gates.py                                |   8 +-
 tests/test_gates_fmt_directives.py                 |  16 ++--
 tests/test_graph.py                                |  34 ++++---
 tests/test_lang.py                                 |  16 +---
 tests/test_tick013_gate.py                         |   4 +-
 tests/test_ticket_evidence.py                      |   4 +-
 tests/test_ticket_leases.py                        |  48 +++++-----
 tests/test_ticket_reconcile.py                     |   4 +-
 tests/test_tickets.py                              |  12 ++-
 tickets/T-2808/done-report.md            | 103 +++++++++++++++++++++
 tickets/T-2808/ticket.md                 |  79 ++++++++++++++++
 16 files changed, 289 insertions(+), 83 deletions(-)
```

### Evidence
- `tests/system/test_cli_ticket.py::TestTicketRoundTrip::test_new_list_doable` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestDigests::test_reformat_identical_digests` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestParsePython::test_symbols_and_nesting` (pytest node id, verified passing when recorded)
- `tests/test_tick013_gate.py::TestTick013EmptyScope::test_in_progress_empty_scope_fires` (pytest node id, verified passing when recorded)
- `tests/test_ticket_reconcile.py::TestReconcileStaleHold::test_dry_run_reports_but_does_not_requeue` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestQueue::test_round_trip_load` (pytest node id, verified passing when recorded)
- `tests/test_ticket_evidence.py::TestSetKind::test_updates_kind_field` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestRefusesTerminalState::test_refuses_done_ticket` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_ticket_promote.py::TestPromoteCLI::test_promoting_an_already_final_id_is_a_no_op` (pytest node id, verified passing when recorded)
- `tests/system/test_fleet_status_ticket_readiness_arch001.py::TestFleetStatusTicketReadinessArch001::test_ticket_readiness_is_not_an_arch001_finding` (pytest node id, verified passing when recorded)
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_fragments_module_fs_read_is_declared_not_selfaudit001` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestAutofixManifest::test_write_then_clear_roundtrip` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestMarkerFor::test_python_uses_hash` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 13 passed (from 13 evidence id(s))
- gates: 21 error(s), 2062 warning(s), 711 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC001@docs/investigations/T-2790-check-stage-profile.md, DOC001@docs/investigations/T-2796-backlog-reproduction.md, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, DUP001@tests/system/test_frob_self_model.py, DUP001@tests/test_graph.py, PERF004@src/frob/tickets/_evidence.py, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
