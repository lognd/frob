+++
id = "01M3AXSDB6A1EHK0WTG8SEEP4D"
title = "STORE209: point `DELETE` on a TimescaleDB hypertable instead of a chunk/partition drop"
type = "task"
category = "todo"
priority = "low"
parent = "01M3AXSD9N6EMFMTKASSQETY9D"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T22:22:26Z"
aliases = ["T-6502"]
labels = ["milestone:0.538.0", "v1-cluster:B1", "area:grimble", "triage:accepted"]
scope = ["src/frob/store/_timeseries.py", "tests/fixtures/store/store209-timescale-point-delete/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD97HRBA035Y3FNX3ACG"
+++

Rule id: STORE209.

Authority: TimescaleDB docs, "About constraints"
(https://docs.timescale.com/use-timescale/latest/schema-management/about-constraints/)
fetched; research file flags this row **gap** -- no standalone
point-delete-cost quote isolated from that specific page this pass, cites
general Timescale architecture instead. Static tier for this row in the
research file is "static: yes for the call shape; needs schema knowledge
(is this table a hypertable) to be non-heuristic -- tag as config",
which is why this leaf lives in Story 2, not Story 1.

Call shapes: `cursor.execute("DELETE FROM hypertable WHERE id = %s",
(row_id,))` in a per-row loop; TS/JS: same shape via node-postgres
against a hypertable.

Repo fact needed: confirm the target table is declared a hypertable
(`create_hypertable(...)` call tracked in a migration file, reuse
`migration_scan`'s tracked-file scan, extended for
`create_hypertable`).

Positive-control fixture:
`tests/fixtures/store/store209-timescale-point-delete/`.

Relevance gate: relational SQL surface AND a `create_hypertable` call
found somewhere in tracked migrations.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
