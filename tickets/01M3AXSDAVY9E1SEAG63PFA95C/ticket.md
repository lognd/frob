+++
id = "01M3AXSDAVY9E1SEAG63PFA95C"
title = "STORE103: `SET`/`SETEX` on a cache-named key with no TTL (Redis)"
type = "task"
category = "triage"
priority = "low"
parent = "01M3AXSD9STSFC2MR8M369JNE8"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T20:59:44Z"
aliases = ["T-6491"]
labels = ["milestone:0.538.0", "v1-cluster:B1", "area:grimble", "triage:accepted"]
scope = ["src/frob/store/_redis.py", "tests/fixtures/store/store103-redis-no-ttl/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD97HRBA035Y3FNX3ACG"
+++

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
