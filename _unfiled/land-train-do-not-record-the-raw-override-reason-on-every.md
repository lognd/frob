+++
id = "01M7EX83J64G6Y4V4DJW6YP80B"
title = "land train: do not record the raw override reason on every member"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-11-15T06:10:24Z"
updated = "2026-11-15T06:10:24Z"
labels = ["no-story"]
+++

Source: frob-audit-core.md L3. Evidence: crates/frob-land/src/train_close.rs:428-440. Remedy: record it once on the train head and reference it from members. Files: train_close.rs.
