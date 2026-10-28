+++
id = "01M5WFSY5XAV6VY4NVXCSTHWPN"
title = "sync_policy.rs clone_with_origin makes independent root commits (timing flake)"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-26T16:13:26Z"
updated = "2026-10-28T12:55:50Z"
labels = ["no-story"]
scope = ["crates/frob/tests/it/sync_policy.rs"]
+++

Same fixture flaw as ~EK0YNZX: origin and clone each commit an empty c1; hashes differ across a second boundary. Use git clone.

no-story: internal engineering task in frob; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
