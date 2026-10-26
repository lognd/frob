+++
id = "01M5WFSY5XAV6VY4NVXCSTHWPN"
title = "sync_policy.rs clone_with_origin makes independent root commits (timing flake)"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-26T16:13:26Z"
updated = "2026-10-26T16:13:26Z"
scope = ["crates/frob/tests/it/sync_policy.rs"]
+++

Same fixture flaw as ~EK0YNZX: origin and clone each commit an empty c1; hashes differ across a second boundary. Use git clone.
