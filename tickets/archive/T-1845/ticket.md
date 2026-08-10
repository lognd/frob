---
id: T-1845
title: Add a land-finish-pending marker around --finish/--retire-on-proof's git mutations
  (T-1554 design follow-up)
state: done
kind: feature
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- tests/unit/test_land_finish_guard.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_land_finish_guard.py
  reason: 'T-1845: unit + SIGTERM-injection tests for the new marker'
  actor: logan
  at: '2026-08-08'
evidence:
- tests/unit/test_land_finish_guard.py::TestLandFinishPendingMarker::test_write_then_clear_round_trips
- tests/unit/test_land_finish_guard.py::TestLandFinishPendingMarker::test_no_marker_is_a_silent_empty_result
- tests/unit/test_land_finish_guard.py::TestLandFinishPendingMarker::test_stale_marker_is_reported
- tests/unit/test_land_finish_guard.py::TestLandFinishPendingMarker::test_reconcile_reports_and_clears_a_stale_marker
- tests/unit/test_land_finish_guard.py::TestLandFinishPendingMarkerSigterm::test_sigterm_between_marker_write_and_mutation_leaves_marker_for_reconcile
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Follow-up from T-1554's design doc (docs/design/land-checkpoint-durability.md):
add a `land-finish-pending/<ticket_id>.json` marker (mirroring T-1523's
`_land_verify_pending_marker_path` shape) around `--finish`/
`--retire-on-proof`'s two git mutations (`_finish_worktree`,
`_delete_worktree_branch` in src/frob/app/ticket_runner/_land_cmd.py) --
the one remaining unmarked, untested-against-a-real-SIGTERM land sub-step
per that document's audit. Write before `_finish_worktree` runs, clear
once both mutations (or the applicable one) complete; reconcile at the
top of the next `frob ticket land` invocation the same way
`_stale_post_land_verify_markers` does for T-1523's own marker. Needs a
load-bearing SIGTERM-injection test, matching T-1523's own precedent
(not a unit-level mock).

Once this marker exists, a `frob ticket land --verify-only <sha>` CLI
entrypoint (T-1554's design doc "Option B") can be scoped as a thin
reader of it in a further follow-up -- do not build that CLI surface
before this marker exists to back it.