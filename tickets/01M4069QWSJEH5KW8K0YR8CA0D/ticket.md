+++
id = "01M4069QWSJEH5KW8K0YR8CA0D"
title = "frob-pm crate: milestone and cycle object model, storage and fold"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 5
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:12:53Z"
updated = "2026-10-03T15:28:17Z"
idempotency_key = "m2-rel-pm-crate"
labels = ["milestone:2", "area:release"]
scope = ["crates/frob-pm/**", "Cargo.toml", "crates/frob-ledger/**"]

[[links]]
kind = "blocked-by"
target = "01M3WYJ81430D3D5QSNCFM8QB0"

[[acceptance]]
text = "Given a milestone object written through the ledger, when the ledger is re-folded from events, then the same milestone state results"
bound = true

[[acceptance]]
text = "Given two concurrent edits of one milestone on different branches, when merged, then no event is lost"
bound = true
+++

New crate frob-pm (cli.md lists cycle verbs under frob-pm). Defines Milestone (version, goal, target or unscheduled, member epics, exit criteria with bound evidence ids) and Cycle (id, start, end, goal, optional capacity_points) as ledger objects whose changes are events appended through Ledger::append, folded like tickets. The storage layout is not fixed by tickets.md 3 (it names the objects only); decide it here, record it as an ADR in docs/decisions and in tickets.md via a docs note on the ticket.
