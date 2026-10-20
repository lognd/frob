+++
id = "01M5D5PZP5BZFRWT9W86STF8MV"
title = "gob-exec: detached spawn API for background refresh"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-20T17:28:28Z"
updated = "2026-10-20T18:06:04Z"
scope = ["crates/gob-exec/**"]

[[acceptance]]
text = "Runner::spawn_detached starts a program with null stdio in its own process group and returns its pid without waiting"
bound = true

[[acceptance]]
text = "spawn_detached honours the tool allowlist and reports a missing program as a typed error"
bound = true
+++

found while working ~EV5KK0X: sync_policy::background_kick spawns std::process::Command under a PROC001 waiver; add a detached spawn to gob_exec::Runner and drop the waiver.
