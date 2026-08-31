---
id: T-3542
title: 'Consolidate ledger maintenance commits: 82 percent of main is chore churn;
  make history substantial'
state: queued
kind: feature
origin: human
created: '2026-08-31'
priority: high
parent: null
tier: epic
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
OWNER REQUEST (2026-08-31): main's history is dominated by automatic
maintenance. MEASURED over the last 300 commits: 247 (82%) are
chore(tickets) machinery -- 109 worktree-mirror commits (one per verb per
ticket), 53 "record land commit for T-x" stubs (one trailing EVERY land),
41 sweep/coordinator ticket filings (one per ticket), 26
scope/body/block/evidence transitions -- versus 53 substantive land
commits and 0 anything-else. The ledger must stay git-tracked (worktrees
and the fleet read it), but the write GRANULARITY is per-verb when it
could be per-event. Owner's bar: commits on main should be substantial --
ideally test-first then implementation, with maintenance consolidated.
This epic tracks the go-forward consolidation (pushed history is never
rewritten). Children carry the design per class. Related: T-3053 (land
saga compose-out-of-tree + CAS publish) -- the land-shape leaf should be
designed against that epic's model, not the current saga.
