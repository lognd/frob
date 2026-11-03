+++
id = "01M6D467QZREM3DA0SY7HABQ01"
title = "grimble-model: PLAN030..PLAN034 waypoint chain rules"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-02T03:17:32Z"
updated = "2026-11-03T05:56:38Z"
labels = ["no-story"]
scope = ["crates/grimble-model/src/plan_check.rs,crates/grimble-model/src/rules/**,crates/grimble-model/tests/corpus/**"]

[[acceptance]]
text = "Rule fires and stays clean in corpus cases, md page examples pass, rules index regenerated."
bound = false
+++

Waypoint chains are unmodeled in plan_index. Follow-up of ~49S8FVJ (PLAN012/013/014/015/018/027 landed in grimble-model plan_check; PLAN001-010 live in grimble-bind).
