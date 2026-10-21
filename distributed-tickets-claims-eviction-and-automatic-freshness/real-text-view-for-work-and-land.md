+++
id = "01M5EFE44WSM03AW4771Y53GFT"
title = "Real --text view for work and land"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-21T05:37:37Z"
updated = "2026-10-21T08:27:36Z"
scope = ["crates/frob-worktree/src/verbs.rs"]
+++

Split from ~5JDQ45M: the remaining everyday verbs still fall back to the generic key dump under --text. Reuse crates/frob/src/text_view.rs table helper.
