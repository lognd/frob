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
updated = "2026-10-07T02:01:29Z"
idempotency_key = "m2-tb-layout-write"
labels = ["milestone:2", "area:mirror", "creates:crates/frob-ledger/src/layout.rs", "creates:crates/frob-ledger/tests/layout.rs", "creates:changelog.d/01M3ZX82Q2N145P3DWVVY4E868.added.md"]
scope = ["crates/frob-ledger/src/layout.rs", "crates/frob-ledger/src/ops.rs", "crates/frob-ledger/src/ledger.rs", "crates/frob-ledger/src/lib.rs", "crates/frob-ledger/tests/layout.rs", "changelog.d/01M3ZX82Q2N145P3DWVVY4E868.added.md"]

[[links]]
kind = "blocked-by"
target = "01M3ZX8141MTBF6G2E6BAD33TS"

[[acceptance]]
text = "Given a new ticket under an epic, when created, then its file is at <epic-slug>/<slug>.md and its events are under .events/<ULID>/"
bound = true

[[acceptance]]
text = "Given a ticket without an epic, when created, then it is at _unfiled/<slug>.md"
bound = true
+++

Implements mirror.md section 1; navigation.md section 2.

Replace the tickets/<ULID>/ticket.md storage by `<top-epic-slug>/<slug>.md` plus `.events/<ULID>/`; the ULID stays canonical in frontmatter and frob never resolves ids through paths.
