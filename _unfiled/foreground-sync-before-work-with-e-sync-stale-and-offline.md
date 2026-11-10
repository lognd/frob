+++
id = "01M5DBVTN06Y1MBT6EDFKR7TYT"
title = "Foreground sync before work with E-SYNC-STALE and --offline --reason"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-20T19:15:58Z"
updated = "2026-11-10T00:34:11Z"
scope = ["crates/frob-worktree/**", "crates/frob/src/**", "crates/frob/tests/it/sync_policy.rs", "docs/**", "crates/frob-ledger/src/freshness.rs", "changelog.d/01M5DBVTN06Y1MBT6EDFKR7TYT.changed.md"]
+++

found while working ~46BECG2. Design D-5: work should sync first, refuse when stale, and accept --offline --reason.
