+++
id = "01M5CW0557C2HYG7KZBV3Y6VBJ"
title = "Claim holds and pauses"
type = "task"
category = "in-progress"
priority = "high"
points = 2
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-20T14:38:42Z"
updated = "2026-10-20T20:33:47Z"
idempotency_key = "dt-DT14"
scope = ["crates/frob-ledger/src/claim_hold.rs"]

[[links]]
kind = "blocked-by"
target = "01M5CW04YABDJW6ZXSWFGTCB9E"
+++

claim hold|resume with reason and end date (max 30 days); blocked, review, train and CI pauses capped at 14 days. See docs/design/distributed-tickets.md.
