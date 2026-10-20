+++
id = "01M5CW04D5QJCJ5S72V8PE22M6"
title = "Freshness in envelopes and W-SYNC/E-SYNC classes"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-20T14:38:42Z"
updated = "2026-10-20T18:41:07Z"
idempotency_key = "dt-DT07"
scope = ["crates/frob/src/refresh_cmd.rs", "crates/frob/src/refresh_cmd/freshness.rs", "crates/frob/tests/it/refresh.rs", "changelog.d/01M5CW04D5QJCJ5S72V8PE22M6.added.md"]

[[links]]
kind = "blocked-by"
target = "01M5CW046DKVK5QSJR8TMEN0F2"
+++

Every envelope reports data age; ranked warnings and errors with remedy and how to silence. See docs/design/distributed-tickets.md.
