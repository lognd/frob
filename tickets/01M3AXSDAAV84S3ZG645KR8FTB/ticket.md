+++
id = "01M3AXSDAAV84S3ZG645KR8FTB"
title = "STORE115: `ALTER TABLE ... UPDATE`/`DELETE` mutation on a high-volume ClickHouse table"
type = "task"
category = "triage"
priority = "low"
parent = "01M3AXSD9STSFC2MR8M369JNE8"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T20:59:27Z"
aliases = ["T-6474"]
labels = ["milestone:0.538.0", "v1-cluster:B1", "area:grimble", "triage:accepted"]
scope = ["src/frob/store/_timeseries.py", "tests/fixtures/store/store115-clickhouse-mutation/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD97HRBA035Y3FNX3ACG"
+++

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
