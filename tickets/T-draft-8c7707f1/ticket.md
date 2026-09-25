---
id: T-draft-8c7707f1
title: STORE1xx call-shape rules
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
parent: T-draft-5b96fa72
tier: story
sprint: store-family
runs_last: false
milestone: 0.538.0
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
body_changes:
- mode: append
  reason: 'DOC006: body names files this ticket will create (T-draft-7ee140de)'
  actor: logan
  at: '2026-09-25'
  old_length: 819
  new_length: 957
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Every research row tagged `Static: yes` in scratchpad/db-paradigm-
research.md whose detector needs nothing beyond the call site itself
(scratchpad/DB-PARADIGM-ASSESSMENT.md's tier 1, "call shape alone,
positive control trivial"). Grouped one leaf per client library so scope
stays disjoint: redis, mongo (pymongo/motor/mongoose), dynamodb (boto3),
neo4j, elasticsearch, clickhouse/timescale/influx, s3, and relational-
paradigm-misuse rows (distinct from the query-optimization SQL10x-130
family -- these are paradigm-fit rows: DB-as-queue, blob-in-relational,
recursive-CTE-as-graph-traversal, not join/index-shape rules). Every rule
leaf is blocked by T-STORE-101-SCAFFOLD, which owns client-library
detection, the shared findings-function shape, and gate/id wiring so no
individual rule leaf re-does that plumbing.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
