---
id: T-4654
title: 'Land kernel: explicit logged state machine prepare -> compose -> publish ->
  post-publish'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: critical
parent: T-4651
tier: story
sprint: null
runs_last: false
milestone: 0.535.0
flavour: user_story
due: null
rank: null
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
no_scope_declared: true
no_scope_declared_reason: 'tier=epic/story rollup for the kernel-decoupling epic:
  all file work lives in the leaf children; this ticket carries no write lease by
  design'
triage_changes:
- field: sprint
  old_value: v0.535.0
  new_value: v0.535.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
- field: flavour
  old_value: null
  new_value: user_story
  reason: 'E2 (T-5766): census-based flavour classification (heuristic per E1''s own
    candidate signal)'
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
LAND concern of the kernel-decoupling epic (T-4651).

Today the land is a hand-compensated saga across four stores (T-3053) spread over ~20 modules (_land.py alone is 8366 lines, _land_cmd.py 7511). Measured consequence this week: composing takes 10-25 minutes and then loses the compare-and-swap publish race to a sibling ledger-only commit and refuses (T-4572); the post-publish sweep reloads a full snapshot inside the land's critical path (T-4634) and holds .frob/derived.lock READ for 30 minutes, idling the serial land queue and blocking the next land.

Target shape -- an EXPLICIT, LOGGED state machine with four named phases:
  prepare      -> gather refs and build ONE snapshot
  compose      -> PURE over that snapshot; no git writes, no ledger writes, no lock acquisition
  publish      -> a single compare-and-swap ref update, with a LEDGER-ONLY FAST PATH that re-merges and retries instead of refusing
  post-publish -> never rebuilds a snapshot, never holds derived.lock across a full check; anything expensive is handed to the async sweep
Each phase transition emits a log line with its inputs, duration and outcome.

Frozen contract: `frob ticket land`'s CLI surface and its refusal vocabulary do not change.
