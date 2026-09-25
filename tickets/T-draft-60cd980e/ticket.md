---
id: T-draft-60cd980e
title: 'coord drain: pipeline the next entry''s pre-land phase during the current
  publish'
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
parent: T-5630
tier: ticket
sprint: null
runs_last: false
milestone: v0.535.0
points: 8
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '8'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
- field: parent
  old_value: null
  new_value: T-5630
  reason: coord drain pipelining belongs to the coord surface epic
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The land pipeline is serial end to end, but only the squash-apply, CAS
publish and ledger write must be. Measured on T-5354: ~5 min of pre-land
work (Tier-A fixes, ty pre-check, scope/leakage scans, rapid scoped
sweep) precede the commit, and ~5 min of post-land work (evidence re-
verification, recompose, publish) follow it. Pipelining the NEXT queue
entry's pre-land phase (in its own worktree, against the dev tip that
will exist once the current land publishes, i.e. the staged squash) while
the current entry is in its post-land phase would raise queue throughput
by roughly 40 percent without touching the CAS guarantees: the next
entry re-checks only that dev did not move since its prepare (it did,
by exactly the current land; re-merge is a fast-forward of its base).
Design: a two-slot drain in `frob coord drain` (COORD tree): slot A
publishing, slot B preparing; B's prepare is discarded if A fails.
Positive control: a drain of three green entries must show overlapping
prepare/publish timestamps and total wall time below the serial sum.
Tiered-safety: automatic, logged; falls back to serial on any prepare
refusal.
