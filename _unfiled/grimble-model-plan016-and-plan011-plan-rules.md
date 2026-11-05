+++
id = "01M6D467FK4WW4H4HB6NTVM2T5"
title = "grimble-model: PLAN016 and PLAN011 plan rules"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-02T03:17:32Z"
updated = "2026-11-05T13:13:23Z"
labels = ["no-story"]
scope = ["crates/grimble-model/src/plan_check.rs,crates/grimble-model/src/rules/**,crates/grimble-model/tests/corpus/**"]

[[acceptance]]
text = "Rule fires and stays clean in corpus cases, md page examples pass, rules index regenerated."
bound = false
+++

PLAN016 was skipped because the stateful/idempotent surface is undecided; PLAN011 needs code first. Follow-up of ~49S8FVJ (PLAN012/013/014/015/018/027 landed in grimble-model plan_check; PLAN001-010 live in grimble-bind).
