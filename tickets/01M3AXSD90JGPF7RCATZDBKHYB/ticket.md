+++
id = "01M3AXSD90JGPF7RCATZDBKHYB"
title = "STORE111: Cartesian product from disconnected `MATCH` patterns (Neo4j)"
type = "task"
category = "triage"
priority = "low"
parent = "01M3AXSD9STSFC2MR8M369JNE8"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T20:58:40Z"
aliases = ["T-6432"]
labels = ["milestone:0.538.0", "v1-cluster:B1", "area:grimble", "triage:accepted"]
scope = ["src/frob/store/_neo4j.py", "tests/fixtures/store/store111-neo4j-disconnected-match/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD8EJE4SFMVFJJF41NMA"

[[links]]
kind = "blocked-by"
target = "01M3AXSD97HRBA035Y3FNX3ACG"
+++

Rule id: STORE111.

Authority: Neo4j's pattern/tuning docs address the mechanism generally
(https://neo4j.com/docs/cypher-manual/current/patterns/reference/); the
research file flags this row as a **gap** -- no standalone verbatim
"Cartesian product" warning was extracted from the fetched pages this
pass, cross-referenced instead from the planner's exhaustive-search
discussion. Blocked by T-STORE-401-GAPS.

Call shapes: `MATCH (a:A), (b:B) RETURN a,b` -- two comma-separated
patterns with no shared variable/relationship between them.

Detection: parse Cypher for multiple comma-separated `MATCH` patterns
with no shared identifier across them.

Positive-control fixture:
`tests/fixtures/store/store111-neo4j-disconnected-match/`.

Relevance gate: neo4j driver import detected.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
