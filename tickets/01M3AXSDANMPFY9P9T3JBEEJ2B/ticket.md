+++
id = "01M3AXSDANMPFY9P9T3JBEEJ2B"
title = "STORE203: Redis as durable primary store with no AOF/RDB persistence config reviewed"
type = "task"
category = "triage"
priority = "medium"
parent = "01M3AXSD9N6EMFMTKASSQETY9D"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-09-25T00:00:00Z"
aliases = ["T-6485"]
labels = ["milestone:0.538.0", "v1-cluster:B1", "area:grimble"]
scope = ["src/frob/store/_redis.py", "tests/fixtures/store/store203-redis-no-persistence-config/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD97HRBA035Y3FNX3ACG"
+++

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


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
