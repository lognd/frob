+++
id = "01M5EA0YHJS87TYJ78FE70J6TS"
title = "mirror run: watermark and ledger-commit handling (pending_commits, write_watermark)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-21T04:03:03Z"
updated = "2026-10-21T04:50:57Z"
scope = ["crates/frob-mirror/src/run.rs", "changelog.d/01M5EA0YHJS87TYJ78FE70J6TS.added.md"]

[[acceptance]]
text = "A clean complete run advances the ledger watermark past the log head, counting only foreign commits as new; failed or rate-limited runs hold it"
bound = true
+++

Driver loop landed in ~F6RCGW1 without watermark/commit handling.
