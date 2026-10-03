+++
id = "01M4069TJA7YJTYSZCATV5ZYFS"
title = "PM033 replenish: ready queue below ready_min (Advisory)"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:12:56Z"
updated = "2026-10-03T16:11:06Z"
idempotency_key = "m2-rel-pm033"
labels = ["milestone:2", "area:release"]
scope = ["crates/frob-pm/src/rules/replenish.rs", "docs/reference/rules/pm/**", "crates/frob-pm/src/rules/mod.rs", "crates/frob-pm/tests/corpus.rs", "crates/frob-pm/tests/mdtest/pm033.md", "crates/frob-check/src/product.rs", "docs/reference/rules/PM033.md", "docs/reference/rules/README.md"]

[[links]]
kind = "blocked-by"
target = "01M4069R19D2KZENDGEH83JZSW"

[[acceptance]]
text = "Given one doable ticket and ready_min 4, when frob check runs, then PM033 fires with the counts"
bound = true

[[acceptance]]
text = "Given four doable tickets, when frob check runs, then PM033 is silent"
bound = false
+++

Counts doable tickets (the same set as `ticket doable`); below [pm] ready_min fires Advisory: "ready queue is N, below M: run frob cycle plan or triage". Advisory never fails the gate.
