+++
id = "01M5CW04QCRZ860BZMT46BECG2"
title = "Publish the claim on work"
type = "task"
category = "in-progress"
priority = "high"
points = 5
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-20T14:38:42Z"
updated = "2026-10-20T19:25:58Z"
idempotency_key = "dt-DT10"
scope = ["crates/frob-worktree/src/claim.rs", "crates/frob-worktree/src/work.rs", "crates/frob-worktree/src/lib.rs", "crates/frob-worktree/tests/claim.rs", "changelog.d/01M5CW04QCRZ860BZMT46BECG2.added.md"]

[[links]]
kind = "blocked-by"
target = "01M5CW049SPSRGGP5ENQD7BPB3"
+++

Create-only push of ticket/<handle>, lease events with clone id and agent label, unrecorded-claim detection, resume on another clone, loser flow. Offline: warn and proceed with an unpublished claim (D-5). Soft ~A2J8C05. See docs/design/distributed-tickets.md.
