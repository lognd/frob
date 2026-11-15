+++
id = "01M7EXVJN765SFPK7ZREK3NHXE"
title = "grimble show: print prose by default"
type = "task"
category = "todo"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-11-15T06:21:02Z"
updated = "2026-11-15T06:21:02Z"
labels = ["no-story"]

[[acceptance]]
text = "grimble show NAME prints numbered prose without --prose"
bound = false
+++

Audit: ~/projects/frob-audit2-grimble.md L1. grimble show requires --prose; make it the default. File: crates/grimble/src/show_cmd.rs.
