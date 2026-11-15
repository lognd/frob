+++
id = "01M7EX81686R8Y8DM4XX9Z41A7"
title = "land --override-base-ci over an open blocks-lands ticket records an audit note"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:10:21Z"
updated = "2026-11-15T06:10:22Z"
labels = ["no-story"]

[[acceptance]]
text = "Override over an open blocks-lands ticket adds a note naming the override (test)"
bound = false

[[acceptance]]
text = "No note is added when no blocker is open"
bound = false
+++

Source: frob-audit-core.md M5. Evidence: crates/frob-land/src/base_ci.rs:464-473 overrides silently when a blocks-lands ticket is open. Remedy: write a ledger note on that ticket naming the landed ticket and reason. Files: crates/frob-land/src/base_ci.rs.
