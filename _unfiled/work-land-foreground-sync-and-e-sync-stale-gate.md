+++
id = "01M5D5PZS2AHFT7Z8C2QX7NQN7"
title = "work/land foreground sync and E-SYNC-STALE gate"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-20T17:28:28Z"
updated = "2026-10-27T02:58:29Z"
scope = ["crates/frob-worktree/src/verbs.rs,crates/frob-land/src/verb.rs"]
+++

found while working ~EV5KK0X: wire sync_policy::foreground_probe and stale_gate into work (with --offline --reason, W-SYNC-OFFLINE) and land.
