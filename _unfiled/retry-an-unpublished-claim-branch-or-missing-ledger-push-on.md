+++
id = "01M5DBVTJ0AFFN3BAWEVE5VTE3"
title = "Retry an unpublished claim branch or missing ledger push on sync"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-20T19:15:58Z"
updated = "2026-11-09T23:15:56Z"
scope = ["crates/frob/src/refresh_cmd.rs", "crates/frob/src/refresh_cmd/**", "crates/frob-worktree/src/claim.rs", "crates/frob-worktree/tests/claim.rs", "docs/design/frob/distributed-tickets.md", "crates/frob/tests/it/refresh.rs", "changelog.d/01M5DBVTJ0AFFN3BAWEVE5VTE3.added.md"]
+++

found while working ~46BECG2. W-CLAIM-UNPUBLISHED is emitted by work; sync (refresh) must retry the create-only push and ledger push.
