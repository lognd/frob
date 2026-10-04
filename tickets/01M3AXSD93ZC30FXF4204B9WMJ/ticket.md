+++
id = "01M3AXSD93ZC30FXF4204B9WMJ"
title = "STORE304: recursive/hierarchical traversal by repeated relational queries when a graph store is declared for the same domain"
type = "task"
category = "triage"
priority = "low"
parent = "01M3AXSDBCZ0WN62JE8P0BQRA2"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T20:58:44Z"
aliases = ["T-6435"]
labels = ["milestone:0.538.0", "v1-cluster:B1", "area:grimble", "triage:accepted"]
scope = ["src/frob/store/_strata_mismatch.py", "tests/fixtures/store/store304-relational-walk-when-graph-declared/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD9RZ5GY6YQ2MDV558BD"
+++

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


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
