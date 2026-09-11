---
id: T-4412
title: Graph cache treats 'database is locked' as corruption and rebuilds
state: queued
kind: bug
origin: human
created: '2026-09-11'
priority: critical
parent: T-4410
tier: story
sprint: v0.531.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/cache.py
- tests/unit/test_graph_cache.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: GIVEN a second connection holds an exclusive lock on cache.db WHEN this process's
    connect path hits sqlite 'database is locked' THEN it performs a bounded busy-wait/retry
    (sqlite busy_timeout) instead of classifying the db as unreadable and rebuilding
  evidence: []
- text: GIVEN a test holds an exclusive lock on cache.db from a second connection
    WHEN the primary process opens the cache THEN the test asserts no rebuild is triggered
    and the busy-wait eventually succeeds or times out cleanly
  evidence: []
- text: GIVEN cache.db is genuinely malformed (not merely locked) WHEN connect runs
    THEN it still self-heals via rebuild as today (T-4159 behavior preserved for real
    corruption)
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
A concurrent full check aborts with 'database is locked' and, before aborting, logs 'cache.connect: unreadable db at .frob/cache.db, rebuilding: database is locked'. src/frob/graph/cache.py's connect path (T-4159's self-heal) classifies a busy-lock the same as unreadable/corrupt and triggers a full rebuild, so every concurrent check or land rebuilds the graph. The primary's .frob/ directory holds cache.db.stale-* leftovers from these spurious rebuilds. Fix: distinguish 'locked' from 'corrupt' and use sqlite's busy_timeout / a bounded retry loop for the former, reserving rebuild-on-open for genuine corruption.