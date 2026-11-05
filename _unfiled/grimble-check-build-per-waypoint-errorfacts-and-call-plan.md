+++
id = "01M6KNPVMX5N5V7PG5T8QFFM4A"
title = "grimble check: build per-waypoint ErrorFacts and call plan::findings_with_facts so PLAN041 fires on real repos"
type = "task"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-04T16:19:09Z"
updated = "2026-11-05T16:53:02Z"
idempotency_key = "followup-k6gamtk-facts"
labels = ["no-story"]
scope = ["crates/grimble-bind/src", "crates/gob-symbols/src"]

[[acceptance]]
text = "grimble check on a repo with an unmapped waypoint reports PLAN041"
bound = false
+++

Remainder of K6GAMTK: findings_with_facts exists but bind() never builds facts, so PLAN041 only fires when a caller supplies them (tests). bind() must derive ErrorFacts per waypoint anchor from gob-symbols and call findings_with_facts.
