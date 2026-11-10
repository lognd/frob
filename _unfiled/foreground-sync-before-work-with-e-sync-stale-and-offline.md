+++
id = "01M5DBVTN06Y1MBT6EDFKR7TYT"
title = "Foreground sync before work with E-SYNC-STALE and --offline --reason"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-20T19:15:58Z"
updated = "2026-11-10T00:13:20Z"
scope = ["crates/frob-worktree/**", "crates/frob/src/**"]
+++

found while working ~46BECG2. Design D-5: work should sync first, refuse when stale, and accept --offline --reason.
