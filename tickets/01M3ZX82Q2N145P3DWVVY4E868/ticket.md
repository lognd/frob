+++
id = "01M3ZX82Q2N145P3DWVVY4E868"
title = "Ticket branch layout: events under .events/<ULID>/ and ticket files at computed paths"
type = "task"
category = "in-progress"
priority = "high"
points = 5
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T03:34:41Z"
updated = "2026-10-07T00:50:22Z"
idempotency_key = "m2-tb-layout-write"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-ledger/src/layout.rs", "crates/frob-ledger/src/ops.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX8141MTBF6G2E6BAD33TS"

[[links]]
kind = "blocked-by"
target = "01M3ZX82K7HX9D2VKT25KS4MV2"

[[acceptance]]
text = "Given a new ticket under an epic, when created, then its file is at <epic-slug>/<slug>.md and its events are under .events/<ULID>/"
bound = false

[[acceptance]]
text = "Given a ticket without an epic, when created, then it is at _unfiled/<slug>.md"
bound = false
+++

Implements mirror.md section 1; navigation.md section 2.

Replace the tickets/<ULID>/ticket.md storage by `<top-epic-slug>/<slug>.md` plus `.events/<ULID>/`; the ULID stays canonical in frontmatter and frob never resolves ids through paths.
