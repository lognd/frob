+++
id = "01M7EXQYHYB9SPCN8ZESJGQYW5"
title = "ticket show displays drop reason; superseded closes require --by"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:19:03Z"
updated = "2026-11-15T06:19:03Z"
labels = ["no-story"]

[[acceptance]]
text = "show prints the drop reason (test)"
bound = false

[[acceptance]]
text = "superseded close without --by errors (test)"
bound = false
+++

Source: frob-audit-meta.md L1. Remedy: render the reason in ticket show and require --by on superseded closes. Files: crates/frob ticket verbs.
