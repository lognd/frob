+++
id = "01M5DDB4ZTR3ZWPJNCMJHN764G"
title = "Feed claim activity observation from sync and refresh"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-20T19:41:48Z"
updated = "2026-11-05T14:26:50Z"
labels = ["found-while-working"]
scope = ["crates/frob-worktree/**", "crates/frob/src/refresh_cmd.rs", "docs/design/frob/distributed-tickets.md"]
+++

Call observe_tip/observe_event (frob-worktree activity.rs) from refresh/sync so idle_secs has data; see distributed-tickets.md.
