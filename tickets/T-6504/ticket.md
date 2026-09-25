---
id: T-6504
title: 'STORE116: row-by-row `INSERT` in a loop instead of a batched write (ClickHouse/InfluxDB)'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-6439
parent: T-6457
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
- tests/fixtures/store/store116-timeseries-row-insert-loop/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'DOC006: body names files this ticket will create (T-6448)'
  actor: logan
  at: '2026-09-25'
  old_length: 1067
  new_length: 1205
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Rule id: STORE116.

Authority: cross-referenced from ClickHouse's "Avoid mutations" column-
oriented-storage framing and InfluxDB's line-protocol batch-write
design; the research file flags the dedicated "batch your inserts"
sentence as not isolated verbatim this pass (structural framing, not a
direct quote -- cite the ClickHouse mutations page quote used in
STORE115 as the load-bearing authority for the column-oriented-storage
rationale shared by both).

Call shapes:
- Python (ClickHouse): `for row in rows: client.command(f"INSERT INTO t
  VALUES ({row})")`
- Python (InfluxDB): `write_api.write(bucket, record=point)` per point
  in a loop
- TS/JS: same per-row loop shape in JS clients

Detection: single-row insert/write call inside a loop over an in-memory
collection -- same DB-call-inside-a-loop shape SQL101/STORE105 already
detect for a different call target; reuse `_orm_rules`'s loop-body
helpers.

Positive-control fixture:
`tests/fixtures/store/store116-timeseries-row-insert-loop/`.

Relevance gate: clickhouse or influxdb client import detected.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
