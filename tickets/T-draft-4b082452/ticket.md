---
id: T-draft-4b082452
title: 'STORE101: `KEYS pattern` in application/production code (Redis)'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
parent: T-draft-8c7707f1
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
- tests/fixtures/store/store101-redis-keys/**
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
Rule id: STORE101.

Authority (Redis docs, "KEYS"): "Use extreme care when using this
command in production environments. It may ruin performance when it is
executed against large databases. This command is intended for
debugging and special operations" --
https://redis.io/docs/latest/commands/keys/ (also documents O(N) time
complexity).

Call shapes:
- Python (redis-py): `redis_client.keys("prefix:*")`
- TS/JS (ioredis/node-redis): `redis.keys('prefix:*')`
- Rust (`redis` crate): `.keys()`

Detection: a call to `.keys(`/`KEYS ` on a resolved redis client
receiver (reuse `_detect.detect_store_clients`'s redis-client alias
table for receiver resolution rather than a bare attribute-name match).

Positive-control fixture: `tests/fixtures/store/store101-redis-keys/`
(one file per language calling `.keys()` on a redis client with no
`SCAN`-based alternative nearby).

Relevance gate: only runs when `detect_store_clients` reports a redis
client import; a repo importing no redis client sees no STORE101
finding.
