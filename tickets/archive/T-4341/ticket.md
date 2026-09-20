---
id: T-4341
title: 'TICK005 cannot fire post ledger-v2 cutover: add v1/v2 dispatch to _tick005_ledger_at_ref'
state: done
kind: bug
origin: human
created: '2026-09-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_tickets_gate.py
- tests/test_gates_tick005.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_gates_tick005.py
  reason: 'T-4341: add v2-ledger regression coverage for TICK005 alongside the code
    fix'
  actor: logan
  at: '2026-09-08'
evidence:
- tests/test_gates_tick005.py::TestTick005MergeStateRegression::test_hand_resolved_conflict_resurrecting_done_ticket_is_flagged
- tests/test_gates_tick005.py::TestTick005MergeStateRegression::test_hand_resolved_conflict_resurrecting_done_ticket_is_flagged_on_v2_ledger
- tests/test_gates_tick005.py::TestTick005MergeStateRegression::test_forward_progress_across_a_merge_is_clean
- tests/test_gates_tick005.py::TestTick005MergeStateRegression::test_forward_progress_across_a_merge_is_clean_on_v2_ledger
- tests/test_gates_tick005.py::TestTick005MergeStateRegression::test_non_merge_commit_never_checked
- tests/test_gates_tick005.py::TestTick005MergeStateRegression::test_archived_ticket_is_not_flagged
designated_repro_test: tests/test_gates_tick005.py::TestTick005MergeStateRegression::test_hand_resolved_conflict_resurrecting_done_ticket_is_flagged_on_v2_ledger
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
TICK005 (_tick005_merge_state_regression, src/frob/gates/_tickets_gate.py) reads the parent ledger via git show ref:tickets.md only (v1-monofile path, no v2 dispatch). tickets.md was deleted repo-wide at the T-2356 ledger-v2 cutover (commit e2ed60480), so every merge commit since has no tickets.md blob at HEAD^1 and _tick005_ledger_at_ref always returns None: TICK005 has been structurally unable to fire since the cutover, not zero-findings-because-clean. The identical bug was already found and fixed once for COV002's _ledger_states_at_base (T-1582), which now dispatches on _store_mode_at_base (v1 vs v2) with a working _ledger_states_at_base_v2 reader in frob/gates/__init__.py. Plan: give _tick005_ledger_at_ref the same v1/v2 dispatch (TICK005 needs the full parsed Ticket, not just state, so check whether the existing frontmatter-only v2 reader suffices or a fuller per-ticket parse is needed); re-measure on a synthetic v2 hand-resolved-merge-conflict fixture before promoting back to error in frob.toml. Found while working T-4331 (frob.toml severity audit).