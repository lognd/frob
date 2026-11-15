+++
id = "01M7EX82P5PK04PJVD1W6KPSAY"
title = "land CI-override note is idempotent"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-11-15T06:10:23Z"
updated = "2026-11-15T06:10:23Z"
labels = ["no-story"]
+++

Source: frob-audit-core.md L2. Evidence: crates/frob-land/src/land.rs:1774-1804 appends a duplicate note on every retry. Remedy: skip if an identical note exists. Files: crates/frob-land/src/land.rs.
