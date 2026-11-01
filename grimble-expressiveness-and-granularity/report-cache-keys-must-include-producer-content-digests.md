+++
id = "01M6BDWBVHP852VS29J82REFNG"
title = "Report cache keys must include producer content digests (catalogue, rule tables), not just a version string"
type = "bug"
category = "in-progress"
priority = "high"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-01T11:28:25Z"
updated = "2026-11-01T11:57:03Z"
scope = ["crates/grimble-check/src/product.rs", "crates/grimble-check/src/report_cache.rs", "crates/grimble-check/src/bind_cache.rs", "docs/design/cohesion.md"]

[[acceptance]]
text = "arch and path report caches are keyed on their rule-table digest; a regression test per cache kind proves a rule-table change misses"
bound = true
+++

~P8QM8BH fixed this for the LOG report only; the arch and path report kinds likely have the same stale-cache hazard.
