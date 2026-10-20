+++
id = "01M5CW05WX0TMSBKDFTPEHB5R3"
title = "Repair code and ledger mismatches"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-20T14:38:43Z"
updated = "2026-10-20T23:03:51Z"
idempotency_key = "dt-DT21"
scope = ["crates/frob-land/src/relaunch.rs", "crates/frob-land/src/land.rs"]

[[links]]
kind = "blocked-by"
target = "01M5CW049SPSRGGP5ENQD7BPB3"
+++

refresh and doctor repair disagreements; land --relaunch for local lands on a diverged base. See docs/design/distributed-tickets.md.
