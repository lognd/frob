---
id: T-draft-0bbefe0c
title: 'STORE201: JSON/JSONB column queried by many distinct paths, no expression
  index (relational)'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
parent: T-draft-8980afab
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
- src/frob/store/_relational.py
- tests/fixtures/store/store201-relational-json-blob-schema/**
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
