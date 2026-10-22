+++
id = "01M5HJDX45JB4H214VWY6M378S"
title = "COH002: skip nested functions that are top-level unit statements"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-22T10:27:39Z"
updated = "2026-10-22T10:27:39Z"
scope = ["crates/grimble-check/**", "docs/**"]
+++

COH003 fixed a quirk where a nested function that is a top-level statement of the unit is not skipped; check COH002 for the same.
