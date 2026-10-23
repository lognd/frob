+++
id = "01M5M1TVWKJPZX3BMF736VJAHT"
title = "Extract shared PathLeaves selector helper from grimble-bind owner into a public helper"
type = "task"
category = "in-progress"
priority = "low"
points = 2
reporter = "lognd"
created = "2026-10-23T09:35:21Z"
updated = "2026-10-23T10:21:16Z"
scope = ["crates/grimble-check/**", "crates/grimble-bind/**"]

[[acceptance]]
text = "layers.rs and grimble-bind owner share one public selector helper with no duplicate"
bound = true
+++

Follow-up of WXQ03KP: PathLeaves is duplicated in grimble-check layers.rs.
