+++
id = "01M5DZJ96SRX543SR1N51DGJH0"
title = "Dedupe evict_one_idle_agent and evict_claim into a shared helper"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-21T01:00:16Z"
updated = "2026-10-21T01:15:56Z"
scope = ["crates/frob-worktree/src/next.rs", "crates/frob-worktree/src/claim_evict.rs", "changelog.d/01M5DZJ96SRX543SR1N51DGJH0.changed.md"]
+++

Extract shared observe/judge logic once ~1N3HRWA releases next.rs. (found while working ~A6CYWAE)
