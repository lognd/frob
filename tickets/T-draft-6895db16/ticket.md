---
id: T-draft-6895db16
title: 'STORE119: poll loop around `SELECT ... WHERE status=''pending''` instead of
  a queue product (relational)'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
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
- tests/fixtures/store/store119-relational-db-as-queue/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'DOC006: body names files this ticket will create (T-draft-7ee140de)'
  actor: logan
  at: '2026-09-25'
  old_length: 1323
  new_length: 1461
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Rule id: STORE119.

Authority: Postgres provides `LISTEN`/`NOTIFY` as a notification
primitive, not a durable queue guarantee; this pattern is well
documented as an anti-pattern in the ecosystem generally, but the
research file flags this row **gap**: this fetch pass did not source a
Postgres-specific "don't use us as a queue" quote. Blocked by
T-STORE-401-GAPS.

Call shapes:
- Python: `cursor.execute("SELECT * FROM jobs WHERE status='pending'
  FOR UPDATE SKIP LOCKED")` in a `while True`/APScheduler poll loop;
  SQLAlchemy session polling on an interval
- TS/JS: `knex('jobs').where('status','pending')` in a `setInterval`
  poll loop
- Rust (sqlx): polling loop with `tokio::time::interval`

Detection: polling loop (`while True`/`setInterval`/timer-decorated
function) containing a `SELECT`/`UPDATE` on a table with job/queue-like
column names (`status`, `pending`, `job`, `queue` substrings).

Positive-control fixture:
`tests/fixtures/store/store119-relational-db-as-queue/`.

Relevance gate: relational SQL surface detected
(`frob.sql._extract.sql_relevance`, reused rather than re-sniffed).

Reuse note: this is the relational-paradigm sibling of SQL10x's own
call-shape scan; import `frob.sql._orm_rules`'s `_iter_nodes`/
`_function_defs` walker helpers rather than re-implementing a second
tree-sitter walk.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
