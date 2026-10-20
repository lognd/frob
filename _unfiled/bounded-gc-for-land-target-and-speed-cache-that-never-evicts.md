+++
id = "01M4P1YTX7FMRTYCRQ08VVT0ZP"
title = "Bounded GC for land-target and speed cache that never evicts the warm set"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
reporter = "lognd"
created = "2026-10-11T18:00:19Z"
updated = "2026-10-13T04:02:20Z"
scope = ["crates/frob-worktree/src/gc/**", "docs/reference/config.md", "docs/schemas/config.json"]

[[acceptance]]
text = "Eviction is LRU by last-use stamp with a size budget; entries used in the last N hours or by any live worktree are never evicted"
bound = true

[[acceptance]]
text = "A before/after timing of frob check and frob land on a warm tree shows no regression"
bound = true

[[acceptance]]
text = "GC runs off the hot path (idle or explicit verb) and reports bytes freed"
bound = true

[[acceptance]]
text = "A test asserts a recently used entry survives GC and a stale one is removed"
bound = true
+++

9.1 GB under .git/frob (land-target 6.8 GB, cache 2.3 GB). Speed first: GC must never slow a land or check.
