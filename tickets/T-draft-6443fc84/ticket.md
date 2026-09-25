---
id: T-draft-6443fc84
title: 'STORE304: recursive/hierarchical traversal by repeated relational queries
  when a graph store is declared for the same domain'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
parent: T-draft-f370cf34
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
- tests/fixtures/store/store304-relational-walk-when-graph-declared/**
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
Rule id: STORE304 (research file section 8, cross-cutting signal #4).

Authority: Neo4j's own traversal-oriented tuning guidance (bounded
variable-length paths, STORE108's own authority) implicitly frames this
as the graph DB's core competency being reimplemented elsewhere --
https://neo4j.com/docs/cypher-manual/current/query-tuning/.

Code shape: a loop that issues a `SELECT ... WHERE parent_id = ?` query
once per tree level/depth, building up a result set across iterations
(keyed on a `parent_id`/`ancestor`-style column) -- this fires only when
strata ALSO declares a graph-paradigm store exists for the same bound
domain/entity (distinguishing it from the relational-only case, which is
merely a style choice absent a declared graph alternative and is out of
this rule's scope).

Detection: reuse the loop-body walker helpers (same family as
STORE105/STORE116/STORE119) for the "query per level" shape, gated by a
strata cross-check: does ANY `store` node in this binding's graph
declare `engine` resolving to `graph` paradigm for the same entity kind.

Positive-control fixture:
`tests/fixtures/store/store304-relational-walk-when-graph-declared/`
(a `.strata` fixture declaring both a relational store AND a graph
store for the same entity, with the relational code path doing the
per-level walk).

Relevance gate: relational SQL surface detected AND a graph-paradigm
`store` node declared elsewhere in the same strata graph.
