+++
id = "01M5CW046DKVK5QSJR8TMEN0F2"
title = "Refresh state and remote probe"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-20T14:38:41Z"
updated = "2026-10-20T16:15:42Z"
idempotency_key = "dt-DT05"
+++

refresh.toml state, bounded non-prompting ls-remote (2.5s), backoff, lock, frob refresh --status under 10ms, remote and base validation. See docs/design/distributed-tickets.md.
