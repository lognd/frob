+++
id = "01M5DFKY3FZKR6EWYR83J8MJQ7"
title = "evict ledger record and crash completion in sync"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-20T20:21:33Z"
updated = "2026-11-11T21:56:01Z"
scope = ["crates/frob-worktree/src/claim_evict.rs", "docs/design/frob/distributed-tickets.md", "crates/frob-worktree/tests/claim_evict.rs"]

[[acceptance]]
text = "Eviction writes the lease op evict event and the in-progress to todo transition naming the previous holder"
bound = true

[[acceptance]]
text = "complete_crashed_eviction finishes a crashed eviction using needs_completion and read_park_record"
bound = true
+++

found while working ~6CVW7F9: lease op evict, in-progress to todo, comment naming previous holder, use needs_completion/read_park_record
