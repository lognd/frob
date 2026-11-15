+++
id = "01M7EX81R2T1ZV6FHYE4J8S97V"
title = "evidence guard: reject records measured at a commit that does not cover the current scope"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:10:22Z"
updated = "2026-11-15T06:10:22Z"
labels = ["no-story"]

[[acceptance]]
text = "Record from an earlier commit with later scope changes is stale (test)"
bound = false

[[acceptance]]
text = "Record with no scoped changes since stays valid (test)"
bound = false
+++

Source: frob-audit-core.md M6. Evidence: crates/frob-evidence/src/guard.rs and record.rs accept a record measured at any earlier commit. Remedy: require the measured commit to be an ancestor with no scoped-file changes since, else stale. Files: crates/frob-evidence/src/guard.rs, record.rs.
