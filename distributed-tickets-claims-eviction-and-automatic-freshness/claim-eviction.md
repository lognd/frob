+++
id = "01M5CW051RTDRTFH0X96CVW7F9"
title = "Claim eviction"
type = "task"
category = "in-progress"
priority = "high"
points = 5
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-20T14:38:42Z"
updated = "2026-10-20T20:11:12Z"
idempotency_key = "dt-DT13"
scope = ["crates/frob-worktree/src/evict.rs", "crates/frob-worktree/src/claim.rs", "crates/frob-worktree/src/lib.rs", "crates/frob-worktree/tests/evict.rs"]

[[links]]
kind = "blocked-by"
target = "01M5CW04YABDJW6ZXSWFGTCB9E"
+++

frob claim evict: park to parked/<handle>-<n>, CAS delete only if tip unmoved, record, crash completion, holder return and --reclaim, batch evict. Human-held claims evict automatically (D-4). See docs/design/distributed-tickets.md.
