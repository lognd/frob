+++
id = "01M3AXSD879R9QFQFYD8ATR031"
title = "STORE109: Cypher query with no `LIMIT` (Neo4j)"
type = "task"
category = "triage"
priority = "low"
parent = "01M3AXSD9STSFC2MR8M369JNE8"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T20:58:11Z"
aliases = ["T-6407"]
labels = ["milestone:0.538.0", "v1-cluster:B1", "area:grimble", "triage:accepted"]
scope = ["src/frob/store/_neo4j.py", "tests/fixtures/store/store109-neo4j-no-limit/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD97HRBA035Y3FNX3ACG"
+++

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
