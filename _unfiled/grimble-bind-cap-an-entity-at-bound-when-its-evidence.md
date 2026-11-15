+++
id = "01M7EXV0P0YXPDKZA9KYWBF32Y"
title = "grimble-bind: cap an entity at bound when its evidence carries TESTQ001"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:20:44Z"
updated = "2026-11-15T06:21:53Z"
labels = ["no-story"]

[[links]]
kind = "blocked-by"
target = "01M7EXV0GGRFVK94Z0XS720HNE"

[[acceptance]]
text = "A fixture with TESTQ001 evidence reports bound, not covered"
bound = false
+++

Audit: ~/projects/frob-audit2-grimble.md M4 (optional part). Remedy: an entity whose evidence carries TESTQ001 cannot rise above bound. Crates: crates/grimble-bind/src/plan.rs.
