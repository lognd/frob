+++
id = "01M5ASPRNKH3X9W5N9FDERAFCQ"
title = "Mirror: ticket-branch ShardStore implementing frob_mirror::mapfile::ShardStore with CAS"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-19T19:20:09Z"
updated = "2026-10-19T19:21:28Z"
scope = ["crates/frob-mirror/src/shardstore.rs", "crates/frob-mirror/Cargo.toml"]
+++

No concrete ShardStore exists (only test Mem impls). Needed by the mirror recreate verb (~1KH6CCV) and push.
