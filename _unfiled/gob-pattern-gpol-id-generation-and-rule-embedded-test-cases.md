+++
id = "01M4XDJTJ71VYA5NX8A9VJZ6EE"
title = "gob-pattern: GPOL id generation and rule-embedded test cases"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-14T14:38:09Z"
updated = "2026-11-05T00:27:36Z"
labels = ["no-story"]
scope = ["crates/gob-pattern/**"]

[[acceptance]]
text = "Given a rules dir, when a new rule is created, then the next free GPOLnnn id is produced and embedded test cases (source plus expected findings/fixed output) run"
bound = true
+++

Split from ~NRQ4KHD.

no-story: internal engineering task in gob-pattern; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
