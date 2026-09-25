---
id: T-draft-ef2a178a
title: 'STORE120: file-read/upload bytes bound directly into an `INSERT`/`UPDATE`
  (blob-in-relational)'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-draft-6a23884f
parent: T-draft-8c7707f1
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
- tests/fixtures/store/store120-relational-blob-insert/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'DOC006: body names files this ticket will create (T-draft-7ee140de)'
  actor: logan
  at: '2026-09-25'
  old_length: 1097
  new_length: 1235
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Rule id: STORE120.

Authority: Postgres itself documents the size/perf tradeoff: TOAST caps
at 1 GB per field and "most operations on a TOASTed field will read or
write the whole value as a unit" versus large objects allowing up to
4 TB with efficient partial I/O -- Postgres 18 docs, "33.1. Introduction"
(Large Objects), https://www.postgresql.org/docs/current/lo-intro.html.

Call shapes:
- Python: `cursor.execute("INSERT INTO files (data) VALUES (%s)",
  (file_bytes,))` where `file_bytes` comes from an uploaded file object;
  SQLAlchemy `Column(LargeBinary)`
- TS/JS: `pg` query with a `Buffer` parameter from `multer`/upload
  middleware, Prisma `Bytes` field fed directly from request body
- Rust (sqlx): `Vec<u8>` bound param from a file read

Detection: binary/bytes parameter sourced from a file-upload/read call,
bound directly into an `INSERT`/`UPDATE` call -- data-flow from
read/upload call to the query call's argument, within one function body.

Positive-control fixture:
`tests/fixtures/store/store120-relational-blob-insert/`.

Relevance gate: relational SQL surface detected.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
