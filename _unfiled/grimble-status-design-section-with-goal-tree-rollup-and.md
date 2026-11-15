+++
id = "01M7EXVHQ2B6GFWWHAV87S71NW"
title = "grimble status: design section with goal tree, rollup and obligations by kind"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:21:01Z"
updated = "2026-11-15T06:21:01Z"
labels = ["no-story"]

[[acceptance]]
text = "status --text prints the goal tree with statuses"
bound = false

[[acceptance]]
text = "Obligations are grouped by kind with file:line"
bound = false

[[acceptance]]
text = "An insta test covers the output"
bound = false
+++

Audit: ~/projects/frob-audit2-grimble.md M7. Evidence: grimble status shows only grants (crates/grimble/src/status_cmd.rs); graph --text prints one line; nothing answers 'what is the state of my design and what next'. Remedy: goal tree, status and rollup, obligations grouped by kind with file:line.
