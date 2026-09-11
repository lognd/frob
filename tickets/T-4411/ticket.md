---
id: T-4411
title: Seed land squash worktree graph cache from primary
state: queued
kind: feature
origin: human
created: '2026-09-11'
priority: critical
parent: T-4410
tier: story
sprint: v0.532.0
runs_last: false
milestone: v0.532.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land_squash.py
- src/frob/graph/cache.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: GIVEN a rapid land creates a disposable squash worktree WHEN the land's synchronous
    check loads the graph THEN the squash worktree's .frob/cache.db is seeded (copy
    or hardlink) from the primary checkout's cache.db before the graph loads, instead
    of rebuilding uncached
  evidence: []
- text: GIVEN the seeded cache is stale for touched files WHEN the check runs THEN
    normal drift detection invalidates and recomputes only the touched entries, not
    the whole graph
  evidence: []
- text: 'GIVEN this fix lands WHEN a land runs THEN the land log no longer prints
    ''load_graph: no cache at /tmp/frob-land-squash-<id>/wt/.frob/cache.db'' for a
    repo with a warm primary cache'
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Every land log prints the verbatim line 'load_graph: no cache at /tmp/frob-land-squash-<id>/wt/.frob/cache.db', showing the land's disposable squash worktree rebuilds the whole graph uncached before checking, which is a large share of the 25-45 minute synchronous land time. Seed the squash/stage worktree's .frob/cache.db from the primary's cache (copy or hardlink) at worktree creation, then let existing drift detection invalidate only touched files. No timing claim is made here (an attempted before/after measurement aborted with a lock error, see the separate cache-locking ticket); acceptance is behavioral (log line gone, correctness via drift detection), with timing to be measured once locking is fixed.