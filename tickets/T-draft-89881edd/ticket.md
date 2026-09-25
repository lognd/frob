---
id: T-draft-89881edd
title: 'STORE204: blocking command (`BLPOP`/`BRPOP`/`WAIT`/long `SUBSCRIBE`) issued
  on a shared/pooled client object'
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
- tests/fixtures/store/store204-redis-blocking-on-shared-conn/**
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
Rule id: STORE204.

Authority: cross-referenced from Redis's client-connection model (a
single connection blocks that command's caller); research file flags
this row **gap** -- no dedicated vendor quote sourced this pass. Blocked
by T-STORE-401-GAPS.

Call shapes: `shared_pool.blpop(...)` where `shared_pool` is the same
client object used elsewhere for request-path `GET`/`SET`; TS/JS:
`sharedClient.blpop(...)` reused as the main app client.

Repo fact needed: trace whether the connection/client object used for
the blocking call is the SAME instance used elsewhere for request-path
calls (identifier-binding trace within the module, not a full alias-
resolution pass -- reuse `frob.vet._capability_python`'s alias-table
shape (`_bind_py_name`/`_py_scope_alias_lookup`) for the same-object
identity check rather than reinventing one).

Positive-control fixture:
`tests/fixtures/store/store204-redis-blocking-on-shared-conn/`.

Relevance gate: redis client detected.
