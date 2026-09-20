---
id: T-5123
title: landing must reap its own branch and worktree and never dev-sync a done ticket's
  worktree
state: queued
kind: bug
origin: human
created: '2026-09-20'
priority: high
parent: T-4651
tier: ticket
sprint: v0.533.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_worktree_sweep.py
- src/frob/tickets/_unlanded.py
- src/frob/tickets/_land_finalize.py
- tests/ticket_land_suite/test_land_reaps_worktree.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.533.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-20: 183 worktrees and 1437 t-* branches exist; T-3797 (done since 2026-09-05) and T-4556 (done 2026-09-19) still had live worktrees, and T-3797's worktree received a merge of dev at 2026-09-20 00:09 from the auto-sync step. Cause: src/frob/tickets/_worktree_sweep.py keeps any branch ahead of main (the keep-verdict near line 431), which a squash-land always leaves behind, so no landed ticket is ever reaped, and sweep_worktrees (line 213) and remove_worktree (line 300) are not on the land path's tail. Fix: teach the ahead-of-main and unlanded verdicts (near line 516) to consult the ticket state on the default branch (src/frob/tickets/_unlanded.py near line 355): a branch whose ticket is done on the default branch is landed-and-squashed and must be reaped; have land call the sweep for its own ticket at the end; make the auto-sync step (T-1720/T-2173) refuse to sync a worktree whose ticket is terminal. Positive control: after a fixture land, the ticket's worktree and branch are gone; a worktree for a done ticket is refused by the sync step.
