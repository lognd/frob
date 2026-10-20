+++
id = "01M5B9ZKNYHSNYFCH1ZPBEEBRK"
title = "Ledger parse_shard: treat a shard without issue as unmapped, not malformed"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-20T00:04:36Z"
updated = "2026-10-20T00:04:36Z"
scope = ["crates/frob-ledger/src/mirror_map.rs"]
+++

found while working ~Q7FE2A0: the branch shard store only writes issue = N once issue_number is known; mirror_issue should return None for a shard with no issue instead of a malformed error. Also consider a real TOML codec in mapfile encode/decode.
