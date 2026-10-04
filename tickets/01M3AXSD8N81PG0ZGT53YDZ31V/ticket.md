+++
id = "01M3AXSD8N81PG0ZGT53YDZ31V"
title = "STORE121: `WITH RECURSIVE` issued in a loop with an increasing depth parameter"
type = "task"
category = "todo"
priority = "low"
parent = "01M3AXSD9STSFC2MR8M369JNE8"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T22:22:24Z"
aliases = ["T-6421"]
labels = ["milestone:0.538.0", "v1-cluster:B1", "area:grimble", "triage:accepted"]
scope = ["src/frob/store/_relational.py", "tests/fixtures/store/store121-relational-recursive-cte-loop/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD97HRBA035Y3FNX3ACG"
+++

Rule id: STORE121.

Authority: cross-referenced from the "workload vs paradigm mismatch"
section (Neo4j's own docs on variable-length paths, STORE108's
authority, apply symmetrically to the relational recursive-CTE case) --
https://neo4j.com/docs/cypher-manual/current/query-tuning/. This is
distinct from the single-call, runtime-unbounded-depth row (dropped, see
T-STORE-DROP-RECURSIVE-DEPTH): this rule flags the STATIC shape of the
CTE call being issued repeatedly in a loop, which is observable without
runtime data.

Call shapes:
- Python: `WITH RECURSIVE` CTE in raw SQL called from app code inside a
  loop with an increasing depth-bound parameter
- TS/JS: `knex.raw("WITH RECURSIVE ...")`, Prisma raw query with
  recursive CTE, inside a loop
- Rust (sqlx): raw `WITH RECURSIVE` inside a loop

Detection: a `WITH RECURSIVE` SQL string literal call inside a `for`/
`while` loop whose loop variable feeds a bound/depth parameter of that
call -- distinguishes this (static: yes, call-in-loop shape) from the
single-call unbounded-depth dropped row (dynamic-only: needs runtime
depth value).

Positive-control fixture:
`tests/fixtures/store/store121-relational-recursive-cte-loop/`.

Relevance gate: relational SQL surface detected.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
