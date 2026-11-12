+++
id = "01M5HJDX45JB4H214VWY6M378S"
title = "COH002: skip nested functions that are top-level unit statements"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T10:27:39Z"
updated = "2026-11-12T22:04:37Z"
labels = ["no-story"]
scope = ["crates/grimble-check/**", "docs/**"]

[[acceptance]]
text = "COH002 does not flag a nested function that is a top-level statement of the unit, covered by a test"
bound = true
+++

COH003 fixed a quirk where a nested function that is a top-level statement of the unit is not skipped; check COH002 for the same.

no-story: internal engineering task in grimble-check; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
