+++
id = "01M5D5PZS2AHFT7Z8C2QX7NQN7"
title = "work/land foreground sync and E-SYNC-STALE gate"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-20T17:28:28Z"
updated = "2026-11-10T05:09:48Z"
labels = ["no-story"]
scope = ["changelog.d/01M5D5PZS2AHFT7Z8C2QX7NQN7.added.md", "crates/frob/tests/it/sync_policy.rs", "crates/frob-land/src/verb.rs", "crates/frob-worktree/src/verbs.rs"]
+++

found while working ~EV5KK0X: wire sync_policy::foreground_probe and stale_gate into work (with --offline --reason, W-SYNC-OFFLINE) and land.

no-story: internal engineering task in frob-worktree; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
