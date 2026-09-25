---
id: T-6501
title: 'SYSDESIGN502: high-write-volume store with no declared partition/shard key'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-6460
parent: T-6429
tier: ticket
sprint: sysdesign
runs_last: false
milestone: 0.539.0
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
- src/frob/sysdesign/_data_tier.py
- tests/fixtures/sysdesign/sysdesign502/**
scope_breadth_ack: true
scope_breadth_ack_reason: sysdesign epic tree, scope reviewed by coordinator
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: SYSDESIGN502: high-write-volume store with no declared partition/shard key
kind: feature
tier: leaf
parent: T-SYS-SG
milestone: 0.539.0
sprint: sysdesign
points: 3
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/sysdesign/_data_tier.py, docs/modules/gates.md (SYSDESIGN502 row),
       tests/fixtures/sysdesign/sysdesign502/**
blocked_by: [T-SYS-A-INFRA-STORE]
tag: Static: design

Research row 8.8: AWS Well-Architected Reliability Pillar REL05-BP01 -- "Amazon Relational
Database Service, like almost all relational databases, can only have one primary writer
instance. This creates a single point of failure for write workloads and makes scaling more
difficult." Lint condition: "A data store declared in the design model as 'high write volume'
with no documented partition/shard key strategy flags."

Reads the `keyed_by`/`shards` store_prop clauses added by T-SYS-A-INFRA-STORE; per the Scaling
Stance section, sharding is explicitly a DEFERRABLE concern ("can be deferred until a single
primary's write capacity is empirically approaching its ceiling") -- this rule therefore only
fires on a store the design model explicitly marks high-write-volume, never as a blanket
requirement on every store.

Acceptance criteria: flags a store with `attr high_write_volume` (or equivalent declared
traffic classification) and no `shards`/`keyed_by` clause. Positive-control fixture:
tests/fixtures/sysdesign/sysdesign502/high-write-store-no-shard-key/**.
