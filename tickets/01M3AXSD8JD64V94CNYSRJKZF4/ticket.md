+++
id = "01M3AXSD8JD64V94CNYSRJKZF4"
title = "STORE101: `KEYS pattern` in application/production code (Redis)"
type = "task"
category = "todo"
priority = "low"
parent = "01M3AXSD9STSFC2MR8M369JNE8"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T22:22:24Z"
aliases = ["T-6418"]
labels = ["milestone:0.538.0", "v1-cluster:B1", "area:grimble", "triage:accepted"]
scope = ["src/frob/store/_redis.py", "tests/fixtures/store/store101-redis-keys/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD97HRBA035Y3FNX3ACG"
+++

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


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
