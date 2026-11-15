+++
id = "01M7EX8087Z0PK5CE004M297GB"
title = "land train: recover from an interrupted advanced run instead of wedging"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-11-15T06:10:21Z"
updated = "2026-11-15T06:10:21Z"
labels = ["no-story"]
+++

Source: frob-audit-core.md M3. Evidence: crates/frob-land/src/train.rs:657-703 and train_close.rs:340-356; a train killed after advancing the base leaves state that later runs cannot reconcile. Remedy: detect the advanced-but-unclosed state and resume or roll back deterministically. Files: crates/frob-land/src/train.rs, train_close.rs.
