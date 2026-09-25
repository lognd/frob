---
id: T-draft-96e59811
title: 'dropped: graph DB used for tabular/columnar (`GROUP BY`-style) aggregation
  over most/all nodes'
state: dropped
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
parent: T-draft-929e1bd0
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
frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"

Research file, Graph anti-pattern #6. Static tier: "dynamic-only
(requires knowing the aggregation touches most/all nodes)" -- a Cypher
`WITH n.category AS c, count(*) AS n RETURN c, n` aggregation is
syntactically indistinguishable from a legitimate bounded aggregation
without knowing what fraction of the graph the (unconstrained) `MATCH
(n)` actually touches at runtime.

Reason: dynamic-only -- becomes a frob:tests / EXPLAIN-style obligation,
never a static rule.

## Drop reason
- 2026-09-25: dynamic-only: becomes a frob:tests / EXPLAIN-style obligation, never a static rule
