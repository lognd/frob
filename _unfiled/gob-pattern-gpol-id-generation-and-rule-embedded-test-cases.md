+++
id = "01M4XDJTJ71VYA5NX8A9VJZ6EE"
title = "gob-pattern: GPOL id generation and rule-embedded test cases"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-14T14:38:09Z"
updated = "2026-10-14T14:38:09Z"
scope = ["crates/gob-pattern/**"]

[[acceptance]]
text = "Given a rules dir, when a new rule is created, then the next free GPOLnnn id is produced and embedded test cases (source plus expected findings/fixed output) run"
bound = false
+++

Split from ~NRQ4KHD.
