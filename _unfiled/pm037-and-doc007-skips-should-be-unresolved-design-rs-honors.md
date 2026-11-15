+++
id = "01M7EXQTRCCBQ63H9ZMY7JQN8N"
title = "PM037 and DOC007 skips should be Unresolved; design.rs honors sibling_timeout_secs"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-11-15T06:18:59Z"
updated = "2026-11-15T06:18:59Z"
labels = ["no-story"]
+++

Source: frob-audit-meta.md M6. Evidence: skipped checks report clean; crates/frob-ledger/src/design.rs:243 ignores sibling_timeout_secs. Remedy: emit Unresolved on skip and pass the configured timeout. Files: PM037/DOC007 rule crates, design.rs.
