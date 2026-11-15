+++
id = "01M7EX84HV979BT7WDFBW6A58W"
title = "land: re-read the ticket after taking the land lock"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-11-15T06:10:25Z"
updated = "2026-11-15T06:10:25Z"
labels = ["no-story"]
+++

Source: frob-audit-core.md L5. Evidence: crates/frob-land/src/land.rs:86,343-385 use ticket state read before the lock. Remedy: re-read status/criteria after lock acquisition. Files: land.rs.
