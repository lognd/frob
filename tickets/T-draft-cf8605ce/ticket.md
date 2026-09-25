---
id: T-draft-cf8605ce
title: 'STORE103: `SET`/`SETEX` on a cache-named key with no TTL (Redis)'
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
- tests/fixtures/store/store103-redis-no-ttl/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'DOC006: body names files this ticket will create (T-draft-7ee140de)'
  actor: logan
  at: '2026-09-25'
  old_length: 857
  new_length: 995
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Rule id: STORE103.

Authority (Redis docs, "EXPIRE"): documents that ordinary write ops
(`LPUSH`, `HSET`, etc.) "leave the timeout untouched" and TTL must be
explicitly set/cleared via `EXPIRE`/`PERSIST` --
https://redis.io/docs/latest/commands/expire/ (vendor documents TTL as
an explicit, separate act from the write).

Call shapes:
- Python: `r.set(key, value)` (no `ex=`/`px=` kwarg), keys named/used as
  cache (`cache:*`, `*_cache`), with no accompanying `EXPIRE` call
- TS/JS: `redis.set(key, value)` with no `EX`/`PX` option,
  `ioredis.set(key, value)`

Detection: call-shape match on `SET`/`SETEX` variants missing the
TTL-bearing argument, cross-referenced with a key-name heuristic (`cache`
substring in the key literal/f-string).

Positive-control fixture: `tests/fixtures/store/store103-redis-no-ttl/`.

Relevance gate: redis client detected.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
