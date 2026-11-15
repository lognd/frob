+++
id = "01M7EX81686R8Y8DM4XX9Z41A7"
title = "land --override-base-ci over an open blocks-lands ticket records an audit note"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-11-15T06:10:21Z"
updated = "2026-11-15T06:10:21Z"
labels = ["no-story"]
+++

Source: frob-audit-core.md M5. Evidence: crates/frob-land/src/base_ci.rs:464-473 overrides silently when a blocks-lands ticket is open. Remedy: write a ledger note on that ticket naming the landed ticket and reason. Files: crates/frob-land/src/base_ci.rs.
