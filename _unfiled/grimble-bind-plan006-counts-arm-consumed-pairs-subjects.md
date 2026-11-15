+++
id = "01M7EXTYXTQNPAEPR1C8R96SGE"
title = "grimble-bind: PLAN006 counts arm-consumed pairs (subjects_examined 0)"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:20:42Z"
updated = "2026-11-15T06:20:42Z"
labels = ["no-story"]

[[acceptance]]
text = "CONF 18.2 sample reports PLAN006 with subjects_examined > 0"
bound = false

[[acceptance]]
text = "PLAN005 fires for both place_order and browse in a fixture test"
bound = false
+++

Audit: ~/projects/frob-audit2-grimble.md M1 (part 2). Evidence: PLAN006 never fires, subjects_examined 0; crates/grimble-bind/src/plan.rs:710-733,879 leaves n.collected empty for scenarios whose pairs are consumed by arms; PLAN005 reported for place_order but not browse. Remedy: feed arm-matched pairs into collected.
