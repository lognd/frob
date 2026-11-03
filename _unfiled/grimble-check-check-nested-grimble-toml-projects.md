+++
id = "01M6EWRXPNTGA5YZEGYVBQGDPD"
title = "grimble check: check nested grimble.toml projects individually"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-02T19:46:25Z"
updated = "2026-11-03T05:56:49Z"
labels = ["no-story"]
scope = ["crates/grimble-check/src/**"]

[[acceptance]]
text = "Each nested grimble.toml project is checked individually, not only logged"
bound = false
+++

Follow-up from ~JHK8825: nested grimble.toml projects are only logged, not checked individually.
