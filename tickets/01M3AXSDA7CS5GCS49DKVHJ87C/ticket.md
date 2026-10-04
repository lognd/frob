+++
id = "01M3AXSDA7CS5GCS49DKVHJ87C"
title = "STORE110: `RETURN n` (bare node/relationship) instead of property projection (Neo4j)"
type = "task"
category = "todo"
priority = "low"
parent = "01M3AXSD9STSFC2MR8M369JNE8"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T22:22:25Z"
aliases = ["T-6471"]
labels = ["milestone:0.538.0", "v1-cluster:B1", "area:grimble", "triage:accepted"]
scope = ["src/frob/store/_neo4j.py", "tests/fixtures/store/store110-neo4j-return-whole-node/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD97HRBA035Y3FNX3ACG"
+++

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
