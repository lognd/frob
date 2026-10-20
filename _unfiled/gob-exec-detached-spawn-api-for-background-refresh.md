+++
id = "01M5D5PZP5BZFRWT9W86STF8MV"
title = "gob-exec: detached spawn API for background refresh"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-20T17:28:28Z"
updated = "2026-10-20T17:35:23Z"
scope = ["crates/gob-exec/**"]
+++

found while working ~EV5KK0X: sync_policy::background_kick spawns std::process::Command under a PROC001 waiver; add a detached spawn to gob_exec::Runner and drop the waiver.
