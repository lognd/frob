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
updated = "2026-10-21T08:32:13Z"
scope = ["crates/frob-worktree/src/verbs.rs", "crates/frob-land/src/verb.rs", "crates/frob-land/src/land_view.rs", "crates/frob-worktree/src/work_view.rs", "crates/frob-land/src/lib.rs", "crates/frob-worktree/src/lib.rs", "changelog.d/01M5EFE44WSM03AW4771Y53GFT.changed.md"]

[[acceptance]]
text = "frob work --text prints a verdict, worktree, branch and lease rows"
bound = false

[[acceptance]]
text = "frob land --text prints a verdict with facts for one ticket and per-ticket lines for a batch"
bound = false
+++

Split from ~5JDQ45M: the remaining everyday verbs still fall back to the generic key dump under --text. Reuse crates/frob/src/text_view.rs table helper.
