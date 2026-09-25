---
id: T-6393
title: 'STORE302: per-request full-collection/table/index scan reachable from a request
  handler, regardless of declared paradigm'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-6456
parent: T-6508
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
- src/frob/store/_strata_mismatch.py
- tests/fixtures/store/store302-full-scan-reachable-from-handler/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'DOC006: body names files this ticket will create (T-6448)'
  actor: logan
  at: '2026-09-25'
  old_length: 1055
  new_length: 1193
- mode: set
  reason: 'DOC006 inline waivers: body names files this ticket will create (T-6448)'
  actor: logan
  at: '2026-09-25'
  old_length: 1193
  new_length: 1282
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
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
