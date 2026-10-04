+++
id = "01M3AXSDB13PEDG5GTC0QP4E87"
title = "dropped: graph DB used for tabular/columnar (`GROUP BY`-style) aggregation over most/all nodes"
type = "task"
category = "done"
outcome = "wont-fix"
priority = "medium"
parent = "01M3AXSD9Z2T54HFHNCZ91W3YV"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-09-25T00:00:02Z"
aliases = ["T-6497"]
labels = ["milestone:0.538.0"]
+++

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
