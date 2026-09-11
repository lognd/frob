---
id: T-4431
title: Land squash worktree rebuilds natives from scratch every land
state: queued
kind: bug
origin: human
created: '2026-09-11'
priority: critical
parent: T-4410
tier: ticket
sprint: v0.531.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land_squash.py
- src/frob/tickets/_land_git_ops.py
- src/frob/strata/_native_staleness.py
- tests/unit/test_land_squash_stage.py
- tests/test_natives.py
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
Every land's disposable squash worktree (created by
compose_squash_in_disposable_worktree in src/frob/tickets/_land_compose.py,
via 'git worktree add --detach -q <tmp>/wt <base_commit>') starts cold on
built natives: the worktree working directory has no compiled artifacts
(they are gitignored, so 'git worktree add' never populates them), so
stale_natives/unimportable_natives report the worktree's own natives as
stale/missing and T-1213's auto-rebuild triggers a full cargo build of
both native cores on every land.

Verbatim log lines observed (measured 2026-09-11, full check inside land:
60-110 minutes vs 305s for the same check in a warm worktree):

  stale_natives: 2 native(s) stale vs their own source: ['strata_core', 'frob_core']
  run_gates: T-1213 auto-rebuild triggered (stale=['frob_core', 'strata_core'], missing=[])
  run_gates: T-1213 auto-rebuild succeeded for [...]

Fix: when the land creates its disposable squash worktree, make the
primary checkout's already-built natives visible to it (copy/hardlink the
compiled artifacts, and/or point the staleness probe at the primary's
build when the worktree's source tree for those crates is identical to
the primary's) so _maybe_autorebuild_natives finds them fresh and skips
the rebuild -- without weakening T-1213's guarantee that a GENUINELY stale
native (source edited relative to what was last built) still rebuilds.

Filed under epic T-4410 (large-project landing cost). Companion ticket
T-4411 (cache.db seeding) covers the "no cache" half of the same cold-
worktree cost; this ticket is the natives-rebuild half.