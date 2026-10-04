+++
id = "01M42MGNZZ1BY6YCG49BDHEZAT"
title = "A ledger commit from a linked worktree reports success while the primary checkout is left with a staged deletion of the new event"
type = "bug"
category = "in-progress"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-10-04T04:59:49Z"
updated = "2026-10-04T13:13:59Z"
scope = ["crates/gob-git/src/ledger.rs"]

[[acceptance]]
text = "Given a ledger commit made from a linked worktree, when it completes, then the primary checkout has no staged deletion, or the result names the checkout that could not be synced"
bound = true
+++

Reproduced. Report checkouts the ledger commit could not sync and give the local-edits refusal a remedy. Evidence and repro: notes/review/v1-gap/D-incidents.md (P-04).
