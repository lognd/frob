---
id: T-draft-324ff873
title: 'frob coord drain [--loop]: the runner in frob, hygiene, housekeeping, engine
  reload'
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: coord-surface
runs_last: false
milestone: v0.535.0
points: null
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
- field: sprint
  old_value: null
  new_value: coord-surface
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob coord drain [--loop]: the runner, in frob. For the head entry: pre-land hygiene as typed Result steps (merge dev into the worktree with dev winning land-owned files, promote drafts, sync all extras, rebuild stale natives, dedupe duplicate draft dirs, discard failure-log residue on the root), then drain_next, then post-land housekeeping per the tiered safety rule (auto-remove clean, unleased, landed worktrees and log; recommend the probably-safe removals; never force). --loop runs it as a daemon honoring a pause file and reloading itself when the land engine's own code lands (the 2026-09-24 lesson: a long-lived drain kept pre-fix code for hours). CAS-race and transient-DirtyMain failures are requeued automatically; a tip that failed for its own reasons is not retried until its worktree has a new commit. Parity control: one recorded success and one recorded CAS-race case from the scratchpad runner behave identically. Cutover is immediate after the parity run; retires queue-runner.sh, land-one.sh, hygiene.sh, dedupe-ledger.sh, prune-worktrees.sh.
