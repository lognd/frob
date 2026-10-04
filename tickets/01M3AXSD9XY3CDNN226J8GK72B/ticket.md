+++
id = "01M3AXSD9XY3CDNN226J8GK72B"
title = "STORE108: variable-length path pattern (`[*]`) with no upper bound (Neo4j)"
type = "task"
category = "triage"
priority = "low"
parent = "01M3AXSD9STSFC2MR8M369JNE8"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T20:59:16Z"
aliases = ["T-6461"]
labels = ["milestone:0.538.0", "v1-cluster:B1", "area:grimble", "triage:accepted"]
scope = ["src/frob/store/_neo4j.py", "tests/fixtures/store/store108-neo4j-unbounded-path/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD97HRBA035Y3FNX3ACG"
+++

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


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
