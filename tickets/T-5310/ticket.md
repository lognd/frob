---
id: T-5310
title: 'Post-land sweep residue 2026-09-22_1719: AFFECT001:tests/unit/perf/test_effect_summaries.py
  COV002:src/frob/_cli_parsers/_shims.py COV002:src/frob/app/docs_runner.py COV002:src/frob'
state: queued
kind: bug
origin: human
created: '2026-09-22'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
Findings raised by a post-land sweep and disposed against this ticket by the coordinator's runner to keep the quarantine clear. Fix each in scope:
AFFECT001:tests/unit/perf/test_effect_summaries.py
COV002:src/frob/_cli_parsers/_shims.py
COV002:src/frob/app/docs_runner.py
COV002:src/frob/gates/_land_parity.py
COV002:tests/gates/test_bug_repro_at_ref_public.py
COV002:tests/system/test_cli_perf.py
COV002:tests/test_gates_test019.py
COV002:tests/test_gates_tick005.py
COV002:tests/test_gates_tick009_tick010.py
COV002:tests/test_gates_tickets_hygiene.py
COV002:tests/test_graph_lock.py
COV002:tests/test_tick012_gate.py
COV002:tests/test_ticket_done_report_claims.py
COV002:tests/test_ticket_land_lint_diff_attribution.py
COV002:tests/test_ticket_runner_done_report.py
COV002:tests/test_tickets_dispatch_stale.py
COV002:tests/test_tickets_lease_overlay.py
COV002:tests/test_tickets_no_scope.py
COV002:tests/test_tickets_own_obligations.py
COV002:tests/test_tickets_rule_shaped.py
COV002:tests/test_tickets_tiers.py
COV002:tests/test_tickets_wave.py
COV002:tests/test_worktree_pythonpath.py
COV002:tests/ticket_land_suite/test_archive.py
COV002:tests/ticket_land_suite/test_draft.py
COV002:tests/ticket_land_suite/test_land_plan.py
COV002:tests/ticket_land_suite/test_release.py
COV002:tests/ticket_land_suite/test_verify_reset.py
COV002:tests/ticket_land_suite/test_waive_deletion.py
COV002:tests/unit/gates/test_win32_kill_signal.py
COV002:tests/unit/test_app_runners_t2395_contention.py
COV002:tests/unit/test_app_style.py
COV002:tests/unit/test_callgraph_module_scoped.py
COV002:tests/unit/test_check_measurement.py
COV002:tests/unit/test_check_runner_formatter_t1276.py
COV002:tests/unit/test_close_blocked_by_guard.py
COV002:tests/unit/test_close_t1648_remainder.py
COV002:tests/unit/test_confinement_lattice.py
COV002:tests/unit/test_cross_ticket_leakage_gate.py
COV002:tests/unit/test_land_orphaned_evidence_node_granularity.py
COV002:tests/unit/test_land_parity_gate.py
COV002:tests/unit/test_lang_artifact_cache.py
COV002:tests/unit/test_logging_module.py
COV002:tests/unit/test_parser_failure_diagnostics.py
COV002:tests/unit/test_reopen_ticket.py
COV002:tests/unit/test_scaffold_managed.py
COV002:tests/unit/test_ticket_new_json.py
COV002:tests/unit/test_tickets_evidence_only_scope.py
COV002:tests/unit/test_wait_for_land_slot_unattributed.py
COV002:tests/vet_suite/test_capability_scan_python.py
COV002:tests/vet_suite/test_supply_chain.py
DOC007:src/frob/docs/_command_pages.py
DRIFT002:src/frob/app/docs_runner.py
DRIFT002:src/frob/docs/_command_pages.py
DSL001:tests/test_mutate_journal.py
DSL001:tests/test_serve_daemon.py
DSL001:tests/test_serve_socket.py
DSL001:tests/unit/gates/test_lock_producer.py
DSL001:tests/unit/strata/test_native_staleness.py
DSL001:tests/unit/test_done_report_check_scope.py
DSL001:tests/unit/test_ticket_runner_gate_findings.py
DUP002:src/frob/gates/_land_parity.py
DUP002:tests/gates/test_rule_id_scan_branches.py
DUP002:tests/test_ticket_land_lint_diff_attribution.py
DUP002:tests/unit/strata/test_backpressure.py
PLACE001:tests/test_refactor.py
PLACE001:tests/test_ticket_reconcile.py
PLACE001:tests/ticket_land_suite/test_claim_close.py
PLACE001:tests/ticket_land_suite/test_ledger_splice.py
PLACE001:tests/unit/test_draft_finalize_attachments.py
REF002:docs/commands/ack.md
REF002:docs/commands/agent.md
REF002:docs/commands/claude.md
REF002:docs/commands/coverage.md
REF002:docs/commands/doctor.md
REF002:docs/commands/explore.md
REF002:docs/commands/natives.md
REF002:docs/commands/pool.md
REF002:docs/commands/profile.md
REF002:docs/commands/registry.md
REF002:docs/commands/status.md
REF002:docs/commands/test.md
REF002:docs/commands/verify.md
REF002:docs/commands/worktree.md
TEST010:frob-core/src/callgraph.rs
TEST010:frob-core/src/r5.rs
TEST010:src/frob/docs/_command_pages.py
TEST010:tests/test_refactor.py
TEST010:tests/test_tickets_leases.py
TEST010:tests/unit/test_ticket_runner_gate_findings.py
TICK010:.git/frob-leases/T-4518.json
TICK010:.git/frob-leases/T-5151.json
WIRE001:src/frob/app/ticket_runner/__init__.py
WIRE001:src/frob/docs/_command_pages.py