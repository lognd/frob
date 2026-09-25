---
id: T-draft-80f967c4
title: 'STORE206: high-cardinality tag column (unique IDs/timestamps/hashes as InfluxDB
  tags)'
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
- src/frob/store/_timeseries.py
- tests/fixtures/store/store206-influx-high-cardinality-tag/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'DOC006: body names files this ticket will create (T-draft-7ee140de)'
  actor: logan
  at: '2026-09-25'
  old_length: 989
  new_length: 1127
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Rule id: STORE206.

Authority: InfluxDB OSS v2 docs, "Resolve high series cardinality":
"Tags containing highly variable information like unique IDs, hashes,
and random strings lead to a large number of series... a primary driver
of high memory usage" and specifically calls out "Writing log messages
to tags... Writing timestamps to tags... Unique tag values that grow
over time" as common causes --
https://docs.influxdata.com/influxdb/v2/write-data/best-practices/resolve-high-cardinality/.

Call shapes: `Point("measurement").tag("request_id", uuid).tag(
"timestamp", ts)` (influxdb-client-python) -- tagging with UUID/
timestamp-like values; TS/JS: `new Point('m').tag('requestId', uuid)`.

Repo fact needed: the tag value's semantic source -- heuristic: variable
name matches `id`/`uuid`/`timestamp`/`hash` bound into `.tag()` rather
than `.field()`.

Positive-control fixture:
`tests/fixtures/store/store206-influx-high-cardinality-tag/`.

Relevance gate: influxdb client detected.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
