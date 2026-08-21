---
id: T-2808
title: 'Reformat batch 11/N: 13 files pending ruff-format (T-2359 child)'
state: done
kind: feature
origin: human
created: '2026-08-21'
priority: medium
parent: T-2359
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/system/test_cli_ticket.py
- tests/system/test_cli_ticket_promote.py
- tests/system/test_fleet_status_ticket_readiness_arch001.py
- tests/system/test_frob_self_model.py
- tests/test_gates.py
- tests/test_gates_fmt_directives.py
- tests/test_graph.py
- tests/test_lang.py
- tests/test_tick013_gate.py
- tests/test_ticket_evidence.py
- tests/test_ticket_leases.py
- tests/test_ticket_reconcile.py
- tests/test_tickets.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/conftest.py
  reason: collides with T-draft-8e8177c3's live lease (T-2373 child worktree) -- swapping
    to the next unclaimed file in the remaining-72 list
  actor: logan
  at: '2026-08-21'
- op: add
  glob: tests/test_ticket_reconcile.py
  reason: swap-in for tests/conftest.py, removed for a lease collision -- keeps batch
    11 at 13 files
  actor: logan
  at: '2026-08-21'
- op: remove
  glob: tests/test_ticket_land.py
  reason: collides with T-draft-8e8177c3's live lease (T-2373 child) -- swap for the
    next unclaimed file
  actor: logan
  at: '2026-08-21'
- op: add
  glob: tests/test_tickets.py
  reason: swap-in to keep batch 11 at 13 files
  actor: logan
  at: '2026-08-21'
evidence:
- tests/system/test_cli_ticket.py::TestTicketRoundTrip::test_new_list_doable
- tests/test_graph.py::TestDigests::test_reformat_identical_digests
- tests/test_lang.py::TestParsePython::test_symbols_and_nesting
- tests/test_tick013_gate.py::TestTick013EmptyScope::test_in_progress_empty_scope_fires
- tests/test_ticket_reconcile.py::TestReconcileStaleHold::test_dry_run_reports_but_does_not_requeue
- tests/test_tickets.py::TestQueue::test_round_trip_load
- tests/test_ticket_evidence.py::TestSetKind::test_updates_kind_field
- tests/test_ticket_leases.py::TestRefusesTerminalState::test_refuses_done_ticket
- tests/system/test_cli_ticket_promote.py::TestPromoteCLI::test_promoting_an_already_final_id_is_a_no_op
- tests/system/test_fleet_status_ticket_readiness_arch001.py::TestFleetStatusTicketReadinessArch001::test_ticket_readiness_is_not_an_arch001_finding
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_fragments_module_fs_read_is_declared_not_selfaudit001
- tests/test_gates.py::TestAutofixManifest::test_write_then_clear_roundtrip
- tests/test_gates_fmt_directives.py::TestMarkerFor::test_python_uses_hash
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 21f1af5ea5af59d5d7d82ec993773daa3c21ed8a
---
Batch 11 of the T-2359 ruff-format-only reformat epic. 13 files re-measured against current main via 'uv run ruff format --check .' (72 files remaining before this batch). Format-only, no semantic changes. Excludes files touched by other in-flight worktrees (T-2373 empty-scope epic rollup, T-2790 docs/investigations, T-2793 rapid_sweep/verify) per fleet_status.py lease check at pick time.