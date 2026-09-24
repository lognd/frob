---
id: T-draft-6fd9ee02
title: 'TIER004: milestone closer -- MSCLOSE001 also requires every child epic done
  or explicitly gapped (MilestoneGap)'
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
blocked_by:
- T-5749
- T-draft-ea1c92d6
parent: T-5748
tier: ticket
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
scope:
- src/frob/gates/_strata_milestone_closure.py
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
TIER004: milestone closer -- wire MSCLOSE001's V-model traversal to also require every child epic done or explicitly gapped, reusing the existing MilestoneGap model (owner decision Q4). Lands at WARN.

Positive control: a milestone with one non-gapped open-epic child fails TIER004; a milestone with all epics done-or-gapped passes and stays quiet.

Doc page: docs/strata/vmodel.md#milestone-scoped-closure

Tree: /tmp/claude-1000/-home-logan-projects-frob/f95beb8e-97d5-4dd4-9038-3ffab8a3a4ea/scratchpad/LEDGER-TIERS-TREE.md (sections 2 and 5; section 5 overrides).
