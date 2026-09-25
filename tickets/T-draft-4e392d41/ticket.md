---
id: T-draft-4e392d41
title: 'STORE121: `WITH RECURSIVE` issued in a loop with an increasing depth parameter'
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
- tests/fixtures/store/store121-relational-recursive-cte-loop/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'DOC006: body names files this ticket will create (T-draft-7ee140de)'
  actor: logan
  at: '2026-09-25'
  old_length: 1238
  new_length: 1376
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
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
