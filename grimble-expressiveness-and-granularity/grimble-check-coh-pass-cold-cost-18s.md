+++
id = "01M6ABTQWDG7TKJDYTZDEYY4PR"
title = "grimble-check coh pass cold cost (~18s)"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-01T01:33:21Z"
updated = "2026-11-01T01:33:21Z"
idempotency_key = "perf-coh-pass"
scope = ["crates/grimble-check/**"]

[[acceptance]]
text = "Cold-cache grimble check coh pass under 3s on this repo, with a count-based regression test"
bound = false
+++

Follow-up of YNRQJ09: coh pass in the architecture stage costs about 18s cold; profile and fix.
