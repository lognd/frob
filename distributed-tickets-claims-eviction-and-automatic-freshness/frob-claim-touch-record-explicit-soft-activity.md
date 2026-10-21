+++
id = "01M5DDB53D00DCC2FVJWHZ3DX9"
title = "frob claim touch: record explicit soft activity"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-20T19:41:49Z"
updated = "2026-10-21T08:28:12Z"
labels = ["found-while-working"]
scope = ["crates/frob-ledger/src/event.rs", "crates/frob-ledger/src/claim_hold.rs", "crates/frob-worktree/src/activity.rs", "crates/frob-worktree/src/next.rs", "crates/frob-worktree/src/claim_evict.rs", "crates/frob/src/lease_cmd.rs", "crates/frob-worktree/tests/claim_touch.rs"]
+++

Verb to mark a claim active without a commit; consumes activity.rs observe_event.
