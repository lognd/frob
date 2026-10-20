+++
id = "01M3AXSDAGXPHDNE84W0BC3QYX"
title = "STORE202: `*_cache`-named table with no expiry column (relational)"
type = "task"
category = "todo"
priority = "low"
parent = "01M3AXSD9N6EMFMTKASSQETY9D"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T22:22:25Z"
aliases = ["T-6480"]
labels = ["milestone:0.538.0", "v1-cluster:B1", "area:grimble", "triage:accepted"]
scope = ["src/frob/store/_relational.py", "tests/fixtures/store/store202-relational-cache-table-no-ttl/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD97HRBA035Y3FNX3ACG"
+++

Rule id: STORE202.

Authority: same family as STORE119/DB-as-cache; Postgres offers no
built-in TTL/eviction primitive, unlike Redis's `EXPIRE` (STORE103's own
authority) -- the absence of the feature is itself the signal, per the
research file's own framing.

Call shapes: table/model literally named `cache`/`*_cache` with
`created_at` but no expiry column, or app code manually `DELETE FROM
cache WHERE created_at < now() - interval`.

Repo fact needed: schema/migration column list for a table matching the
`*cache*` name heuristic (reuse `migration_scan`).

Positive-control fixture:
`tests/fixtures/store/store202-relational-cache-table-no-ttl/`.

Relevance gate: relational SQL surface detected.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
