---
id: T-draft-2524fe6e
title: 'STORE205: leading/trailing `LIKE`/`ILIKE ''%x%''` on a column with no trigram/tsvector
  index'
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
- tests/fixtures/store/store205-relational-like-no-index/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'DOC006: body names files this ticket will create (T-draft-7ee140de)'
  actor: logan
  at: '2026-09-25'
  old_length: 1060
  new_length: 1198
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Rule id: STORE205.

Authority: PostgreSQL wiki "Don't Do This"
(https://wiki.postgresql.org/wiki/Don%27t_Do_This) fetched but no
verbatim LIKE-specific quote isolated this pass -- research file flags
this **gap**, citing instead PostgreSQL "12. Full Text Search",
https://www.postgresql.org/docs/current/textsearch.html as the
documented alternative (title confirmed via TOC structure, body not
separately fetched). Blocked by T-STORE-401-GAPS.

Call shapes: `cursor.execute("... WHERE col LIKE %s", (f"%{q}%",))`,
Django `.filter(col__icontains=q)`, SQLAlchemy
`.filter(Model.col.ilike(f"%{q}%"))`; TS: `knex.whereRaw("col LIKE ?",
[`%${q}%`])`, Prisma `{ contains: q }`, TypeORM `Like(`%${q}%`)`; Rust:
sqlx `LIKE $1` with leading wildcard.

Repo fact needed: no matching GIN/trigram index exists on the queried
column (reuse `migration_scan`'s index registry, extended to `CREATE
INDEX ... USING gin`/`gist` statements).

Positive-control fixture:
`tests/fixtures/store/store205-relational-like-no-index/`.

Relevance gate: relational SQL surface detected.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
