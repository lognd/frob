+++
id = "01M5DBVTCDGK4Z096B1ZXVW75J"
title = "Resume a claim on another clone as the same actor"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-20T19:15:57Z"
updated = "2026-11-09T23:31:27Z"
scope = ["crates/frob-worktree/**", "crates/frob-ledger/src/event.rs", "crates/frob-ledger/src/claim_hold.rs", "docs/design/frob/distributed-tickets.md", "changelog.d/01KZ7KGKHYQ1QZ0BHKB49P22KK.changed.md", "changelog.d/01M1QDTYR2FFF5HYHVZP2W1WMP.fixed.md", "changelog.d/01M1QDTYRJ3P3GT8828GCNECVB.added.md", "changelog.d/01M1T07NW78MGWRF7HZQMPSRAV.security.md"]
+++

found while working ~46BECG2. Fetch the remote ticket branch and record a lease move event instead of reporting E-CLAIM-LOST; publish currently only recognises ancestry-of-local as resumed.
