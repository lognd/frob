---
id: T-draft-36ec3173
title: 'STORE109: Cypher query with no `LIMIT` (Neo4j)'
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
- src/frob/store/_neo4j.py
- tests/fixtures/store/store109-neo4j-no-limit/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'DOC006: body names files this ticket will create (T-draft-7ee140de)'
  actor: logan
  at: '2026-09-25'
  old_length: 699
  new_length: 837
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Rule id: STORE109.

Authority: Neo4j Cypher Manual, "Query tuning" (same page as STORE108):
emphasizes selecting/returning only needed data and bounding patterns;
general Cypher guidance recommends `LIMIT` for exploratory/paginated
queries -- https://neo4j.com/docs/cypher-manual/current/query-tuning/.

Call shapes: Cypher string with a `RETURN` clause and no `LIMIT` clause,
executed from a request handler (Python/TS neo4j driver `.run(...)`
calls).

Detection: parse the Cypher string literal for `LIMIT` clause presence,
same string-literal-inspection shape as STORE108.

Positive-control fixture:
`tests/fixtures/store/store109-neo4j-no-limit/`.

Relevance gate: neo4j driver import detected.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
