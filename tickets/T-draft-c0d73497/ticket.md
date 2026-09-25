---
id: T-draft-c0d73497
title: 'STORE203: Redis as durable primary store with no AOF/RDB persistence config
  reviewed'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
parent: T-draft-8980afab
tier: ticket
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
scope:
- src/frob/store/_redis.py
- tests/fixtures/store/store203-redis-no-persistence-config/**
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
Rule id: STORE203.

Authority: Redis docs, "Redis persistence": "No persistence: You can
disable persistence completely. This is sometimes used when caching...
RDB is NOT good if you need to minimize the chance of data loss in case
Redis stops working" --
https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/.

Call shapes: app code that never reads from a secondary DB and treats
`r.set`/`r.get` as the only write path for entities carrying
business-critical data (same shape in Node).

Repo fact needed: `redis.conf`/deployment config `appendonly`/`save`
settings, cross-referenced against "is Redis the only writer for this
entity" (a coarse per-entity writer count, not a full data-flow
analysis).

Positive-control fixture:
`tests/fixtures/store/store203-redis-no-persistence-config/`.

Relevance gate: redis client detected.
