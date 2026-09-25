---
id: T-6484
title: 'STORE114: `script_fields`/inline `script` evaluated per-document in a request
  handler (Elasticsearch)'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-6439
- T-6414
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
- tests/fixtures/store/store114-es-script-fields-hotpath/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'DOC006: body names files this ticket will create (T-6448)'
  actor: logan
  at: '2026-09-25'
  old_length: 858
  new_length: 996
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
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
