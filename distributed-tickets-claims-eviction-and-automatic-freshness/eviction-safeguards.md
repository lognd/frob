+++
id = "01M5CW05P3TPW64S6Y4N95T88M"
title = "Eviction safeguards"
type = "task"
category = "in-progress"
priority = "high"
points = 2
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-20T14:38:43Z"
updated = "2026-10-20T21:52:34Z"
idempotency_key = "dt-DT19"
scope = ["crates/frob-worktree/src/evict.rs", "crates/frob-worktree/tests/evict.rs", "changelog.d/01M5CW05P3TPW64S6Y4N95T88M.added.md"]

[[links]]
kind = "blocked-by"
target = "01M5CW051RTDRTFH0X96CVW7F9"
+++

Flap guard, 5 per person per day rate limit, claim restore. See docs/design/distributed-tickets.md.
