---
id: T-draft-9b8d4b16
title: 'STORE110: `RETURN n` (bare node/relationship) instead of property projection
  (Neo4j)'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-draft-6a23884f
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
- tests/fixtures/store/store110-neo4j-return-whole-node/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'DOC006: body names files this ticket will create (T-draft-7ee140de)'
  actor: logan
  at: '2026-09-25'
  old_length: 679
  new_length: 817
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Rule id: STORE110.

Authority: Neo4j Cypher Manual, "Query tuning": "returning whole nodes
and relationships ought to be avoided in favour of selecting and
returning only the data that is needed" --
https://neo4j.com/docs/cypher-manual/current/query-tuning/.

Call shapes: `session.run("MATCH (n:Person) RETURN n")` (bare node
variable in `RETURN`, no `.property` projection) -- same shape across
Python/TS/JS neo4j drivers.

Detection: parse the `RETURN` clause in the Cypher string literal for a
bare identifier vs a property-access/alias list.

Positive-control fixture:
`tests/fixtures/store/store110-neo4j-return-whole-node/`.

Relevance gate: neo4j driver import detected.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
