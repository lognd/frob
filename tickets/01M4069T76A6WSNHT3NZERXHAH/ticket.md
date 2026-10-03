+++
id = "01M4069T76A6WSNHT3NZERXHAH"
title = "Repository WIP limit: work and start refuse past [pm.wip] in_progress, naming holders"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:12:55Z"
updated = "2026-10-03T15:28:20Z"
idempotency_key = "m2-rel-wip-repo"
labels = ["milestone:2", "area:release"]
scope = ["crates/frob-lease/**", "crates/frob-worktree/**", "frob.toml", "docs/design/architecture.md", "docs/design/tickets.md", "docs/design/releases.md", "docs/reference/config.md", "docs/reference/config.schema.json", "docs/schemas/config.json"]

[[links]]
kind = "blocked-by"
target = "01M3Z71361PCFXV5VKSACRF17G"

[[links]]
kind = "blocked-by"
target = "01M4069R19D2KZENDGEH83JZSW"

[[acceptance]]
text = "Given two tickets in progress and limit 2, when work takes a third, then it exits 3 naming both holders"
bound = true

[[acceptance]]
text = "Given limit 0, when work runs, then no WIP check applies"
bound = true
+++

Enforce [pm.wip] in_progress (this repository: 2, the disk rule) in work and start with exit 3 E-WIP-REPO naming the current holders, next to the existing per-holder limit ([lease] wip_per_holder, also surfaced as [pm.wip] in_progress_per_identity). Limit 0 is off. Sets in_progress = 2 in this repository's frob.toml.
