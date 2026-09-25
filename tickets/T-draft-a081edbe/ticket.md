---
id: T-draft-a081edbe
title: 'STORE115: `ALTER TABLE ... UPDATE`/`DELETE` mutation on a high-volume ClickHouse
  table'
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
- src/frob/store/_timeseries.py
- tests/fixtures/store/store115-clickhouse-mutation/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'DOC006: body names files this ticket will create (T-draft-7ee140de)'
  actor: logan
  at: '2026-09-25'
  old_length: 807
  new_length: 945
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Rule id: STORE115.

Authority: ClickHouse Docs, "Avoid mutations": "As a rule, avoid
frequent or large-scale mutations, especially on high-volume tables.
Instead, use alternative table engines such as ReplacingMergeTree or
CollapsingMergeTree" -- https://clickhouse.com/docs/en/optimize/avoid-mutations.

Call shapes:
- Python (clickhouse_connect): `.command("ALTER TABLE t UPDATE col=...
  WHERE ...")` or `.command("ALTER TABLE t DELETE WHERE ...")`
- TS/JS (clickhouse-js): `client.command({ query: 'ALTER TABLE t UPDATE
  ...' })`
- Go (clickhouse-go): `Exec("ALTER TABLE ... UPDATE ...")`

Detection: parse the SQL string literal for `ALTER TABLE ...
UPDATE`/`DELETE`.

Positive-control fixture: `tests/fixtures/store/store115-clickhouse-mutation/`.

Relevance gate: clickhouse client import detected.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
