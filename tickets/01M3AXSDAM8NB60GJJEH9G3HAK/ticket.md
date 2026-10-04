+++
id = "01M3AXSDAM8NB60GJJEH9G3HAK"
title = "STORE114: `script_fields`/inline `script` evaluated per-document in a request handler (Elasticsearch)"
type = "task"
category = "triage"
priority = "low"
parent = "01M3AXSD9STSFC2MR8M369JNE8"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T20:59:37Z"
aliases = ["T-6484"]
labels = ["milestone:0.538.0", "v1-cluster:B1", "area:grimble", "triage:accepted"]
scope = ["src/frob/store/_elasticsearch.py", "tests/fixtures/store/store114-es-script-fields-hotpath/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD8EJE4SFMVFJJF41NMA"

[[links]]
kind = "blocked-by"
target = "01M3AXSD97HRBA035Y3FNX3ACG"
+++

Rule id: STORE114.

Authority: cross-referenced from Elasticsearch's "Tune for search
speed" page
(https://www.elastic.co/guide/en/elasticsearch/reference/current/tune-for-search-speed.html);
research file flags this row **gap** -- a standalone script-field-cost
quote was not isolated from the stripped page text this pass. Blocked by
T-STORE-401-GAPS.

Call shapes:
- Python: `es.search(body={"script_fields": {...}})` inside a per-
  request handler
- TS/JS: `client.search({ script_fields: {...} })` in a request handler

Detection: call-shape match on the `script_fields`/inline `script` key
presence, plus call-site = request handler (reuse the same reachability
helper as STORE106/STORE107).

Positive-control fixture:
`tests/fixtures/store/store114-es-script-fields-hotpath/`.

Relevance gate: elasticsearch client import AND web framework detected.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
