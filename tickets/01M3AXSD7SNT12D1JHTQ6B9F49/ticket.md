+++
id = "01M3AXSD7SNT12D1JHTQ6B9F49"
title = "STORE302: per-request full-collection/table/index scan reachable from a request handler, regardless of declared paradigm"
type = "task"
category = "triage"
priority = "low"
parent = "01M3AXSDBCZ0WN62JE8P0BQRA2"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T20:57:37Z"
aliases = ["T-6393"]
labels = ["milestone:0.538.0", "v1-cluster:B1", "area:grimble", "triage:accepted"]
scope = ["src/frob/store/_strata_mismatch.py", "tests/fixtures/store/store302-full-scan-reachable-from-handler/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD9RZ5GY6YQ2MDV558BD"
+++

Rule id: STORE302 (research file section 8, cross-cutting signal #2).

Authority: cross-paradigm -- MongoDB "Indexes" page (scan-without-index
framing, https://www.mongodb.com/docs/manual/indexes/), Elasticsearch
"Paginate search results" (shard-load-into-memory framing,
https://www.elastic.co/guide/en/elasticsearch/reference/current/paginate-search-results.html).

Code shape: a query call with no filter/`WHERE`/`match`/predicate
argument, located inside a function reachable from an HTTP route handler
(call-graph reachability from a router decorator/registration).

Detection: reuses the light call-graph reachability helper T-STORE-106/
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its scaffold" -->STORE107/STORE114 already build against `frob.webapp.detect_frameworks`
route markers, applied uniformly across every declared store paradigm
rather than per-client-library (this rule is paradigm-agnostic by
design, per the research row).

Positive-control fixture:
`tests/fixtures/store/store302-full-scan-reachable-from-handler/`.

Relevance gate: any store client import detected AND web framework
detected.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
