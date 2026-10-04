+++
id = "01M3AXSDB8D4EWCTCGD09CJ83S"
title = "STORE116: row-by-row `INSERT` in a loop instead of a batched write (ClickHouse/InfluxDB)"
type = "task"
category = "triage"
priority = "low"
parent = "01M3AXSD9STSFC2MR8M369JNE8"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T20:59:53Z"
aliases = ["T-6504"]
labels = ["milestone:0.538.0", "v1-cluster:B1", "area:grimble", "triage:accepted"]
scope = ["src/frob/store/_timeseries.py", "tests/fixtures/store/store116-timeseries-row-insert-loop/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD97HRBA035Y3FNX3ACG"
+++

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
