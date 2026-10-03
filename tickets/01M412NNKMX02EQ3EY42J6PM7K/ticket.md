+++
id = "01M412NNKMX02EQ3EY42J6PM7K"
title = "This repository: [pm.wip] in_progress = 4 now that sccache halves worktree builds"
type = "chore"
category = "in-progress"
priority = "medium"
points = 1
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T14:28:44Z"
updated = "2026-10-03T14:30:42Z"
idempotency_key = "m2-wip-four-sccache"
labels = ["milestone:2"]
scope = ["frob.toml"]

[[acceptance]]
text = "Given frob.toml, when read, then [pm.wip] in_progress is 4 with a comment giving the reason"
bound = true
+++

Measured 2026-10-03: with sccache as the worktree rustc wrapper, a clean workspace test build went from 110 s (cold cache) to 58 s (warm cache, 376 of 376 compilations hit). The coordinator raises concurrent building agents from 2 to 3; with the coordinator's own design tickets the repository WIP limit becomes 4.
