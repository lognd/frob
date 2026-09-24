---
id: T-5748
title: 'ledger tiers: milestones, epics, user stories and quality objectives, tickets'
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: story
sprint: ledger-tiers
runs_last: false
milestone: v0.536.0
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
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Quality-objective-shaped restructuring of the ledger itself: add a milestone tier, story flavours (user_story | quality_objective), due/rank fields, per-tier closers TIER001-006 (landing as WARN, promoted to ERROR by a final leaf), tiered auto-close, depth lint and promote verbs, and a migration pass over the 39 stories, 42 epics and 11 kind: invariant tickets. Scope is the union of the leaves below.

Owner decisions (2026-09-24): a quality objective derives its V-model level from the invariant it binds (explicit level optional, wins on conflict); every story has at least one child ticket (frob ticket new --tier story --with-ticket for one-change stories); the 11 kind: invariant tickets become quality-objective stories each with one evidence-carrying child, then kind: invariant is retired; TIER004 reuses MSCLOSE001's MilestoneGap; TIER001-006 land WARN and a final leaf promotes them to ERROR after E2/E3 (T-0969 pattern).

Tree: /tmp/claude-1000/-home-logan-projects-frob/f95beb8e-97d5-4dd4-9038-3ffab8a3a4ea/scratchpad/LEDGER-TIERS-TREE.md (sections 2 and 5; section 5 overrides).
