+++
id = "01M5EBD66SH12P69KWVXA8K2NC"
title = "land: audit verb or coord status row listing queued worktrees with dropped hunks (reuse hunk_presence::dropped_hunks)"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-21T04:27:12Z"
updated = "2026-10-21T08:31:41Z"
scope = ["crates/frob-land/src/hunk_presence.rs", "crates/frob-land/src/train.rs", "crates/frob-land/tests/land.rs", "changelog.d/01M5EBD66SH12P69KWVXA8K2NC.added.md"]

[[acceptance]]
text = "frob train status lists queued tickets whose branch history has a base merge that dropped their own hunks"
bound = false
+++

Follow-up from ~JHA8CYK.
