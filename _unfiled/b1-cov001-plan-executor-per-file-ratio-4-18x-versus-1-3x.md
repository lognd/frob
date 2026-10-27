+++
id = "01M5CCZCTVBEHSFE93RRR0WAK8"
title = "B1 COV001: plan executor per-file ratio 4.18x versus 1.3x target"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-20T10:16:09Z"
updated = "2026-10-27T02:58:28Z"
scope = ["crates/gob-plan/src/exec/**"]
+++

Remaining gap after ~BA2A6ST. Suspects: link and path resolution joins, BTreeMap attribute lookups, KindTest::member. Profile with perf on the b1 bench binary.
