---
id: T-6403
title: 'STORE104: non-atomic `GET`-then-conditional-`SET` check-then-set race (Redis)'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-6439
parent: T-6457
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
- tests/fixtures/store/store104-redis-check-then-set/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'DOC006: body names files this ticket will create (T-6448)'
  actor: logan
  at: '2026-09-25'
  old_length: 761
  new_length: 899
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Rule id: STORE104.

Authority (Redis docs, "SET"): documents `NX`/`XX`/`GET` options as the
atomic alternative to separate GET+SET --
https://redis.io/docs/latest/commands/set/ (NX/XX option documentation
present in the command reference).

Call shapes:
- Python: `if not r.get(key): r.set(key, value)` (two separate calls,
  no lock)
- TS/JS: `if (!(await redis.get(key))) { await redis.set(key, value) }`

Detection: reuse `_orm_rules._function_defs`/`_iter_nodes` to find a
`GET` call immediately followed by a conditional `SET` on the same key
literal within the same function body, without `NX` present in the `SET`
call's arguments.

Positive-control fixture:
`tests/fixtures/store/store104-redis-check-then-set/`.

Relevance gate: redis client detected.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
