---
id: T-draft-96dd07bd
title: 'Reformat batch 11/N: 13 files pending ruff-format (T-2359 child)'
state: queued
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
- tests/test_ticket_land.py
- tests/test_ticket_leases.py
- tests/test_ticket_reconcile.py
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
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Batch 11 of the T-2359 ruff-format-only reformat epic. 13 files re-measured against current main via 'uv run ruff format --check .' (72 files remaining before this batch). Format-only, no semantic changes. Excludes files touched by other in-flight worktrees (T-2373 empty-scope epic rollup, T-2790 docs/investigations, T-2793 rapid_sweep/verify) per fleet_status.py lease check at pick time.