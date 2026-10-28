+++
id = "01M3AXSD8F53T8AV3AAY5YVZ5R"
title = "STORE112: `from`/`size` paging beyond the 10,000-hit window (Elasticsearch)"
type = "task"
category = "todo"
priority = "low"
points = 2
parent = "01M3AXSD9STSFC2MR8M369JNE8"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-28T12:57:45Z"
aliases = ["T-6415"]
labels = ["milestone:0.538.0", "v1-cluster:B1", "area:grimble", "triage:accepted", "no-story"]
scope = ["src/frob/store/_elasticsearch.py", "tests/fixtures/store/store112-es-deep-pagination/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD97HRBA035Y3FNX3ACG"
+++

Rule id: STORE112.

Authority: Elasticsearch Reference, "Paginate search results": "By
default, you cannot use from and size to page through more than 10,000
hits. This limit is a safeguard set by the index.max_result_window index
setting. If you need to page through more than 10,000 hits, use the
search_after parameter instead" --
https://www.elastic.co/guide/en/elasticsearch/reference/current/paginate-search-results.html.

Call shapes:
- Python: `es.search(index=idx, body={"from": n, "size": s})` where
  `n+s` can exceed 10000, or `n` grows in a loop
- TS/JS (elasticsearch-js): `client.search({ from: n, size: s })` with
  the same growth pattern

Detection: static match for literal `from`/`size` constants exceeding
10000; config/dynamic tier for `from` values computed from a page-number
variable (out of this leaf's static-only scope -- flag the literal-
constant case only, per the research row's own static-tier split).

Positive-control fixture: `tests/fixtures/store/store112-es-deep-pagination/`.

Relevance gate: elasticsearch-py (or equivalent JS client) import
detected.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"

no-story: internal engineering task in src/frob; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
