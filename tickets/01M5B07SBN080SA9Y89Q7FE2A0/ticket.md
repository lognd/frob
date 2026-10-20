+++
id = "01M5B07SBN080SA9Y89Q7FE2A0"
title = "Mirror: shard store writes .json under .mirror/map but ledger parse_shard expects .toml"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-19T21:14:18Z"
updated = "2026-10-20T00:06:47Z"
scope = ["crates/frob-mirror/src/shardstore.rs", "docs/design/mirror.md"]

[[acceptance]]
text = "The shard store writes .toml files carrying issue = N, and get returns the exact bytes put"
bound = true
+++

found while working ~1KH6CCV
