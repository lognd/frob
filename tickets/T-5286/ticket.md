---
id: T-5286
title: T-5034's fresh-graph fix broke test_unreadable_graph_fails's mockability
state: done
kind: bug
origin: human
created: '2026-09-22'
priority: high
parent: null
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: null
points: 2
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/app/ticket_runner/__init__.py
- tests/unit/test_ticket_runner_land_release.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
evidence:
- tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_unreadable_graph_fails
- tests/ticket_land_suite/test_release.py::TestRealCallbackStaleWorktreeManifest::test_stale_worktree_manifest_still_lands_main_plus_one
designated_repro_test: tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_unreadable_graph_fails
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5286
branch: t-5286
---
Found while burning down CI run 35717833933 (dev tip 197238c35e). My own T-5034 fix (already landed) changed _required_release_bump in src/frob/app/ticket_runner/_land_cmd.py to call frob.graph.build_graph directly instead of the mockable _ticket_runner._graph_snapshot(root) helper, to fix a real stale-cache bug. This broke tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_unreadable_graph_fails, which monkeypatches ticket_runner._graph_snapshot to return Err("boom") and expects _apply_release_bump_for_land to propagate that as Err(LandError.ReleaseBumpFailed) -- since the production code no longer calls _graph_snapshot at all, the monkeypatch has no effect and the test fails with Ok(None) instead.

Fix: extract the fresh-build logic (the same fix T-5034 made) into a new, separately-testable function in src/frob/app/ticket_runner/__init__.py (e.g. _fresh_graph_snapshot(root), calling build_graph directly, no cache-trust fast path) -- _land_cmd.py calls THAT instead of inlining frob.graph.build_graph. Update test_unreadable_graph_fails to monkeypatch _fresh_graph_snapshot instead of _graph_snapshot. This preserves T-5034's own correctness fix (never trust a stale cached snapshot for the REL001 bump computation) while restoring this test's mockability.

Verify with: tests/unit/test_ticket_runner_land_release.py (full file) plus tests/ticket_land_suite/test_release.py::TestRealCallbackStaleWorktreeManifest::test_stale_worktree_manifest_still_lands_main_plus_one (T-5034's own original regression test, must still pass).