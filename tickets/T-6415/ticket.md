---
id: T-6415
title: 'STORE112: `from`/`size` paging beyond the 10,000-hit window (Elasticsearch)'
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
- src/frob/store/_elasticsearch.py
- tests/fixtures/store/store112-es-deep-pagination/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'DOC006: body names files this ticket will create (T-6448)'
  actor: logan
  at: '2026-09-25'
  old_length: 1092
  new_length: 1230
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
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
