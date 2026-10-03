+++
id = "01M4069VZVMHVZ15RSPZQRNCXY"
title = "Classes of service: ticket class field and the expedite lane"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:12:57Z"
updated = "2026-10-03T15:41:25Z"
idempotency_key = "m2-rel-classes"
labels = ["milestone:2", "area:release"]
scope = ["crates/frob-ledger/src/model.rs", "crates/frob-ledger/src/ops.rs", "crates/frob-worktree/**", "crates/frob-lease/src/store.rs", "crates/frob-lease/tests/lease.rs", "crates/frob-ledger/benches/ledger.rs", "crates/frob-ledger/src/doc.rs", "crates/frob-ledger/src/event.rs", "crates/frob-ledger/src/fold.rs", "crates/frob-ledger/src/index.rs", "crates/frob-ledger/src/schema.rs", "crates/frob-ledger/tests/ledger.rs", "crates/frob/src/ticket/mod.rs", "crates/frob/src/ticket/write.rs", "crates/frob/tests/ticket.rs", "crates/gob-dev/src/import_v1.rs", "docs/design/tickets.md"]

[[links]]
kind = "blocked-by"
target = "01M4069T76A6WSNHT3NZERXHAH"

[[acceptance]]
text = "Given limit 2 reached, when work takes an expedite ticket, then it is granted as the single exception"
bound = false

[[acceptance]]
text = "Given one expedite already running, when a second is taken, then it exits 3"
bound = false
+++

Add `class` (expedite, fixed-date, standard, intangible; default standard) to the ticket model and `ticket new/update --class`; an expedite ticket may exceed the repository WIP limit by one, at most [pm.classes] expedite_max at a time; doable orders fixed-date by due. The intangible share check (PM014 per releases.md; pm-enforcement lists PM014 as milestone forecast, a numbering conflict) is out of scope.
