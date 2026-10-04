+++
id = "01M3AXSD7RG6X49SK1GRXSBM8Q"
title = "STORE201: JSON/JSONB column queried by many distinct paths, no expression index (relational)"
type = "task"
category = "triage"
priority = "medium"
parent = "01M3AXSD9N6EMFMTKASSQETY9D"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-09-25T00:00:00Z"
aliases = ["T-6392"]
labels = ["milestone:0.538.0", "v1-cluster:B1", "area:grimble"]
scope = ["src/frob/store/_relational.py", "tests/fixtures/store/store201-relational-json-blob-schema/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD97HRBA035Y3FNX3ACG"
+++

Rule id: STORE201.

Authority: PostgreSQL 18 docs, "8.14 JSON Types": "most applications
should prefer to store JSON data as jsonb, unless there are quite
specialized needs" (framing jsonb as a column-type choice, not the
model) -- https://www.postgresql.org/docs/current/datatype-json.html.

Call shapes: `cursor.execute("... ->> %s ...")`, SQLAlchemy
`Column(JSONB)` queried by many distinct top-level paths, Django
`JSONField` with frequent `__` lookups into it; TS: `pg` raw SQL with
`->>`, Prisma `Json` field type with repeated `path` filters, Knex
`.whereRaw("data->>")`; Rust: sqlx `Json<T>` queried by path repeatedly.

Repo fact needed: column DDL type is `json`/`jsonb` (reuse
`frob.sql._orm_rules.migration_scan`'s tracked-`.sql`-file scan rather
than re-parsing migrations) plus a count of distinct `->`/`->>`/`@>`
path expressions issued against that column across the codebase.

Detection: DDL column type check plus distinct-path-expression count
above a threshold.

Positive-control fixture:
`tests/fixtures/store/store201-relational-json-blob-schema/`.

Relevance gate: relational SQL surface detected.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
