+++
id = "01M7EXV03WGNP1A819GW8AZ0F9"
title = "grimble-bind: impl waypoint chains count as realizations for PLAN004 and status"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:20:43Z"
updated = "2026-11-15T06:20:43Z"
labels = ["no-story"]

[[acceptance]]
text = "A chain-only impl no longer raises PLAN004"
bound = false

[[acceptance]]
text = "Its status rises above declared in a test"
bound = false
+++

Audit: /home/logan/projects/frob-audit2-grimble.md M3 (small part). Evidence: chain-only impl gets PLAN004 and stays declared. Crates: crates/grimble-bind/src/plan.rs.
