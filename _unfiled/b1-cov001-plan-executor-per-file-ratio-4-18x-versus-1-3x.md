+++
id = "01M5CCZCTVBEHSFE93RRR0WAK8"
title = "B1 COV001: plan executor per-file ratio 4.18x versus 1.3x target"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-20T10:16:09Z"
updated = "2026-11-15T02:21:13Z"
labels = ["no-story"]
scope = ["crates/gob-plan/src/exec/**"]

[[acceptance]]
text = "Bounded reaches closures keep the budget, may-edge and frontier verdicts after the hashed breadth-first search"
bound = true
+++

Remaining gap after ~BA2A6ST. Suspects: link and path resolution joins, BTreeMap attribute lookups, KindTest::member. Profile with perf on the b1 bench binary.

no-story: internal engineering task in gob-plan; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
