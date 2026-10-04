+++
id = "01M3AXSD9VB1ZA53CHRAMFY9DS"
title = "STORE102: unbounded `SMEMBERS`/`HGETALL`/`LRANGE key 0 -1` (Redis)"
type = "task"
category = "triage"
priority = "low"
parent = "01M3AXSD9STSFC2MR8M369JNE8"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T20:59:12Z"
aliases = ["T-6459"]
labels = ["milestone:0.538.0", "v1-cluster:B1", "area:grimble", "triage:accepted"]
scope = ["src/frob/store/_redis.py", "tests/fixtures/store/store102-redis-unbounded-read/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD97HRBA035Y3FNX3ACG"
+++

Rule id: STORE102.

Authority (Redis docs): "SMEMBERS": "Time complexity: O(N) where N is
the set cardinality" (https://redis.io/docs/latest/commands/smembers/);
"HGETALL": "O(N) where N is the size of the hash"
(https://redis.io/docs/latest/commands/hgetall/); "LRANGE": "O(S+N)... N
is the number of elements in the specified range"
(https://redis.io/docs/latest/commands/lrange/) -- vendor documents
these as linear/unbounded by construction, unlike O(1) point ops.

Call shapes:
- Python: `r.smembers(key)`, `r.hgetall(key)`, `r.lrange(key, 0, -1)`
  with no `SSCAN`/`HSCAN` pagination alternative used nearby
- TS/JS: `redis.smembers(key)`, `redis.hgetall(key)`,
  `redis.lrange(key, 0, -1)`
- Rust: `redis` crate equivalents

Detection: call-shape match on the three names, with the literal
`0, -1` range flagged directly for `LRANGE`.

Positive-control fixture:
`tests/fixtures/store/store102-redis-unbounded-read/`.

Relevance gate: redis client detected.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
