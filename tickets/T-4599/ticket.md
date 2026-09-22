---
id: T-4599
title: instrument the silent ~111s land phase between rapid --files scoping and worktree
  auto-sync with phase-transition logging
state: done
kind: feature
origin: human
created: '2026-09-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- tests/unit/test_land_phase_elapsed_logging.py
- tests/unit/test_land_auto_rebase.py
- tests/unit/test_land_cmd_drain_wiring.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: instrument the silent land phase with _LandPhaseElapsedFilter-covered logging
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/ticket_land_suite/*
  reason: phase-transition logging tests
  actor: logan
  at: '2026-09-19'
- op: remove
  glob: tests/ticket_land_suite/*
  reason: wrong glob, using real test files instead
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/unit/test_land_phase_elapsed_logging.py
  reason: positive controls for the new checkpoint log lines
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/unit/test_land_auto_rebase.py
  reason: positive controls for the new checkpoint log lines
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/unit/test_land_cmd_drain_wiring.py
  reason: positive control for the new post-land-sweep-dispatch phase marker
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/unit/test_land_cmd_drain_wiring.py
  reason: positive control for the new post-land-sweep-dispatch phase marker
  actor: logan
  at: '2026-09-19'
evidence:
- tests/unit/test_land_auto_rebase.py::TestAutoSyncWorktreeOntoMain::test_logs_a_phase_marker_before_starting_the_merge
- tests/unit/test_land_cmd_drain_wiring.py::TestPostLandSweepDispatchPhaseMarker::test_entry_marker_logged_unconditionally
- tests/unit/test_land_cmd_drain_wiring.py::TestPostLandSweepDispatchPhaseMarker::test_entry_marker_logged_even_on_dry_run
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-4599 why-file finding: T-3233's successful land (08:38:51-08:42:02, /tmp/land-T-3233.log) shows NO phase-transition log at all between [+30.7s] (rapid --files scoped to 9 files) and [+141.6s] (auto-synced worktree onto dev) -- a single 110.9s silent block, 58% of the land's total ~191s wall time, covering commit assembly/claims-reverify/git-add-fallback/REL001-bump/rapid-sweep-dispatch with nothing to attribute it to a specific step. Add _LandPhaseElapsedFilter-covered phase-transition log lines through that span (mirroring T-4417's existing coverage of the earlier phases) so the dominant land-time cost is measurable, not just noticed after the fact.