---
id: T-6502
title: 'STORE209: point `DELETE` on a TimescaleDB hypertable instead of a chunk/partition
  drop'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-6439
parent: T-6453
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
- tests/fixtures/store/store209-timescale-point-delete/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'DOC006: body names files this ticket will create (T-6448)'
  actor: logan
  at: '2026-09-25'
  old_length: 1121
  new_length: 1259
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
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
