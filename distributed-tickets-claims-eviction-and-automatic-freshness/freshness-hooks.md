+++
id = "01M5CW04M17256SKGTF195YEC4"
title = "Freshness hooks"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-20T14:38:42Z"
updated = "2026-10-20T18:29:14Z"
idempotency_key = "dt-DT09"
scope = ["crates/frob/src/freshness_hooks.rs", "crates/frob/src/init.rs", "crates/frob/tests/it/freshness_hooks.rs"]

[[links]]
kind = "blocked-by"
target = "01M5CW04GHM970H5KR4EV5KK0X"
+++

git post-checkout and post-merge hooks, agent session-start hook via frob agent sync, loop and cron docs. Reversible and idempotent. See docs/design/distributed-tickets.md.
