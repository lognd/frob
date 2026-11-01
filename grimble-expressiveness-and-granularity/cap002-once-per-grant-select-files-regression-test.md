+++
id = "01M6ABTR2AWBBW7M9T7EJ8Y6Y1"
title = "CAP002 once-per-grant select_files regression test"
type = "task"
category = "in-progress"
priority = "high"
points = 2
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-01T01:33:21Z"
updated = "2026-11-01T03:25:24Z"
idempotency_key = "perf-cap002-test"
scope = ["crates/grimble-bind/src/caps.rs,crates/grimble-bind/tests/**"]

[[acceptance]]
text = "A count-based test proves cap002 runs select_files once per grant"
bound = false
+++

Follow-up of YNRQJ09: no regression test covers the cap002 quadratic fix.
