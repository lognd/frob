+++
id = "01M7EX841HZKEFX7YBKRF2CFQZ"
title = "base-CI gate: cancelled checks and unreadable blockers fail closed to Pending"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-11-15T06:10:24Z"
updated = "2026-11-15T06:10:24Z"
labels = ["no-story"]
+++

Source: frob-audit-core.md L4. Evidence: crates/frob-land/src/base_ci.rs:238-249,358-367 fail open on cancelled checks and an unreadable blocker list. Remedy: treat as Pending/refuse with a clear message. Files: base_ci.rs.
