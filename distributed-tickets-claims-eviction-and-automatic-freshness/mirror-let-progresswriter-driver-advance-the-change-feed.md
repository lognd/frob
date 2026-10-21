+++
id = "01M5EBMAH736FC0T6RK27P2JFM"
title = "mirror: let ProgressWriter/driver advance the change_feed index cursor"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-21T04:31:06Z"
updated = "2026-10-21T06:48:15Z"
scope = ["crates/frob-mirror/src/host.rs"]

[[acceptance]]
text = "The driver advances the index change_feed cursor to the feed cursor after a clean, completed run that reconciled every feed item, and holds it otherwise"
bound = true
+++

ProgressWriter rewrites the index so the host cannot set change_feed; re-read is idempotent via needs_history. found while working R2MH98S
