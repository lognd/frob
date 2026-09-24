---
id: T-5630
title: 'Coordinator, agent and CI command surface: frob coord, frob agent brief/precheck,
  frob ci'
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
Owner decision 2026-09-24: the coordinator's tooling moves into frob under three stems. frob agent (per-worktree: env exists; add brief and precheck), frob coord (new stem, per-repo coordinator operations run from the root: status, queue reorder/repair/requeue, drain with --loop daemon mode, quarantine dispose --file-residue, freeze/unfreeze, watch), frob ci (T-2982's command surface: report, validity, watch; coord watch subscribes to it). frob fleet stays the cross-repo estate verb (T-0573). Tree, decisions and review: scratchpad COORD-TREE.md (2026-09-24). Tiered safety rule for every side effect: guaranteed-safe runs automatically and is logged; probably-safe is reported as a recommendation with the command; a real decision needs an explicit flag. Retires the scratchpad scripts queue-runner.sh, land-one.sh, hygiene.sh, dedupe-ledger.sh, park.py, prune-queue.py, cas-requeue.sh, dispose-noise.sh, prune-worktrees.sh.
