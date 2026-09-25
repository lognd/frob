---
id: T-draft-2b081a93
title: 'STORE113: wildcard query with a leading wildcard (Elasticsearch)'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
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
- src/frob/store/_elasticsearch.py
- tests/fixtures/store/store113-es-leading-wildcard/**
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
Rule id: STORE113.

Authority: Elasticsearch Reference, "Wildcard query": example pattern
`ki*y` shown as the supported shape --
https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-wildcard-query.html.
Research file flags this **partial gap**: the dedicated
"leading-wildcards-are-expensive" caveat sentence was not isolated
verbatim this pass. Blocked by T-STORE-401-GAPS.

Call shapes:
- Python: `es.search(body={"query": {"wildcard": {"field": {"value":
  f"*{term}"}}}})`
- TS/JS: `client.search({ query: { wildcard: { field: { value:
  `*${term}` } } } })`

Detection: parse the wildcard value string literal/f-string for a
leading `*`.

Positive-control fixture: `tests/fixtures/store/store113-es-leading-wildcard/`.

Relevance gate: elasticsearch client import detected.
