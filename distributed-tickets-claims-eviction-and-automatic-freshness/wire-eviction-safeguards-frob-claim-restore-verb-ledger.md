+++
id = "01M5DN9Q57S88B7DQQH8BAXZ01"
title = "Wire eviction safeguards: frob claim restore verb, ledger restore op, repeat-eviction board flag"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-20T22:00:50Z"
updated = "2026-10-20T23:27:19Z"
scope = ["crates/frob-worktree/src/verbs.rs", "crates/frob-worktree/src/lib.rs", "crates/frob-worktree/src/claim_restore.rs", "crates/frob-worktree/tests/claim_restore.rs", "changelog.d/01M5DN9Q57S88B7DQQH8BAXZ01.added.md"]
+++

Follow-up of N95T88M: call flap_review, rate_left and restore from the CLI/ledger/board.
