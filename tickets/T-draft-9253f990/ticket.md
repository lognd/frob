---
id: T-draft-9253f990
title: 'STORE108: variable-length path pattern (`[*]`) with no upper bound (Neo4j)'
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
- tests/fixtures/store/store108-neo4j-unbounded-path/**
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
Rule id: STORE108.

Authority: Neo4j Cypher Manual, "Query tuning": "You should also make
sure to set an upper limit on variable-length patterns, so they don't
cover larger portions of the dataset than needed" --
https://neo4j.com/docs/cypher-manual/current/query-tuning/.

Call shapes:
- Python (neo4j driver): `session.run("MATCH (a)-[*]-(b) RETURN a,b")`,
  a Cypher string built without a bound on `*`
- TS/JS (neo4j-driver): `session.run('MATCH (a)-[*]-(b) ...')`
- Rust/Go neo4j driver: same string shape

Detection: same string-literal-inspection shape `frob.sql._extract`
already uses for SQL literal detection (this is query-language parsing
of a string-in-call, not a second parser) -- regex/parse for `[*` not
followed by `..N]` or `N]` in a Cypher string literal.

Positive-control fixture:
`tests/fixtures/store/store108-neo4j-unbounded-path/`.

Relevance gate: neo4j driver import detected.
