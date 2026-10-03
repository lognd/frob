+++
id = "01M4069T2V69X32EP8NZQHJH6H"
title = "frob cycle plan fills a cycle from ready work in rank order"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:12:55Z"
updated = "2026-10-03T15:28:20Z"
idempotency_key = "m2-rel-cycle-plan"
labels = ["milestone:2", "area:release"]
scope = ["crates/frob-pm/src/cycle/plan.rs", "crates/frob/src/cycle_cmd.rs"]

[[links]]
kind = "blocked-by"
target = "01M4069SHBAEWRX9WWCSS2FEHN"

[[links]]
kind = "blocked-by"
target = "01M4069SYRHMYXCFAZH0AN408B"

[[acceptance]]
text = "Given ready tickets and a capacity, when cycle plan runs, then it lists the fill in rank order and the left-out tickets with reasons"
bound = false

[[acceptance]]
text = "Given --apply, when plan runs, then the tickets are assigned"
bound = false
+++

Proposes a commitment: doable tickets by rank until capacity, respecting dependencies, preferring tickets of the next milestone, printing what it left out and why; `--apply` assigns through cycle assign. Never over-commits.
