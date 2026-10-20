+++
id = "01M5CW04GHM970H5KR4EV5KK0X"
title = "Per-verb auto-refresh policy"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-20T14:38:42Z"
updated = "2026-10-20T17:15:18Z"
idempotency_key = "dt-DT08"

[[links]]
kind = "blocked-by"
target = "01M5CW049SPSRGGP5ENQD7BPB3"

[[links]]
kind = "blocked-by"
target = "01M5CW04D5QJCJ5S72V8PE22M6"
+++

Background kick for reads (never network inline), foreground 3s budget for work, doable and land, stale_error 24h refusal for mutating verbs, off in CI. See docs/design/distributed-tickets.md.
