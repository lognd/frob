---
id: T-draft-8d885618
title: 'STORE102: unbounded `SMEMBERS`/`HGETALL`/`LRANGE key 0 -1` (Redis)'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-draft-6a23884f
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
- tests/fixtures/store/store102-redis-unbounded-read/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'DOC006: body names files this ticket will create (T-draft-7ee140de)'
  actor: logan
  at: '2026-09-25'
  old_length: 964
  new_length: 1102
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
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
