+++
id = "01M3AXSD9PXH34SF9M9D71CSNJ"
title = "STORE204: blocking command (`BLPOP`/`BRPOP`/`WAIT`/long `SUBSCRIBE`) issued on a shared/pooled client object"
type = "task"
category = "todo"
priority = "low"
parent = "01M3AXSD9N6EMFMTKASSQETY9D"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T22:22:25Z"
aliases = ["T-6454"]
labels = ["milestone:0.538.0", "v1-cluster:B1", "area:grimble", "triage:accepted"]
scope = ["src/frob/store/_redis.py", "tests/fixtures/store/store204-redis-blocking-on-shared-conn/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD8EJE4SFMVFJJF41NMA"

[[links]]
kind = "blocked-by"
target = "01M3AXSD97HRBA035Y3FNX3ACG"
+++

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


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
