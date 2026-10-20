+++
id = "01M5CW05BZQR83F5SJTQEH8MRN"
title = "frob work --next"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-20T14:38:43Z"
updated = "2026-10-20T21:18:10Z"
idempotency_key = "dt-DT16"
scope = ["crates/frob-worktree/src/lib.rs", "crates/frob-worktree/src/next.rs", "crates/frob-worktree/src/verbs.rs", "crates/frob-worktree/tests/next.rs", "changelog.d/01M5CW05BZQR83F5SJTQEH8MRN.added.md", "docs/design/cli.md"]

[[links]]
kind = "blocked-by"
target = "01M5CW04QCRZ860BZMT46BECG2"

[[links]]
kind = "blocked-by"
target = "01M5CW051RTDRTFH0X96CVW7F9"
+++

Atomic allocate and claim with retry. See docs/design/distributed-tickets.md.
