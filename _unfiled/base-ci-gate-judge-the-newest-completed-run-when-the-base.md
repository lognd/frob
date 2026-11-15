+++
id = "01M7EX8ZT4098FYEGSF1FP0W7M"
title = "base-CI gate: judge the newest completed run when the base tip is pending or cancelled"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:10:53Z"
updated = "2026-11-15T06:10:53Z"
labels = ["no-story"]

[[acceptance]]
text = "Pending tip with a green ancestor run is judged green-with-note (test)"
bound = false
+++

Source: frob-audit-meta.md M3. Evidence: base_ci.rs treats a pending/cancelled tip as no signal. Remedy: fall back to the newest completed run on an ancestor. Files: crates/frob-land/src/base_ci.rs.
