+++
id = "01M7EXW578VS2HR1AB6DG9GPXK"
title = "grimble-bind: implement rank-3 pack inference ([[infer]], attr infer = pack::rule)"
type = "task"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-15T06:21:21Z"
updated = "2026-11-15T06:21:21Z"
labels = ["no-story"]

[[acceptance]]
text = "An entity with attr infer binds via a pack rule in a fixture"
bound = false

[[acceptance]]
text = "inference-unavailable is only raised when the pack lacks the rule"
bound = false
+++

Audit: ~/projects/frob-audit-grimble-crunk.md L4. crates/grimble-bind/src/lib.rs:9,17-26; crates/grimble-check/src/packs.rs:1-7; binding.md:282-325. Every attr infer entity gets SYS004 inference-unavailable. Remedy: implement [[infer]].
