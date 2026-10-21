+++
id = "01M5E0F8MC9XT2PCCB9XG6E8X3"
title = "Persist claim holds, pauses and reclaim records (lease op hold/resume/reclaim)"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-21T01:16:06Z"
updated = "2026-10-21T01:29:29Z"
idempotency_key = "dt14-persist-hold-store"
scope = ["crates/frob-ledger/src/event.rs", "crates/frob-ledger/src/claim_hold.rs", "crates/frob-worktree/src/lib.rs", "crates/frob-worktree/src/claim_hold.rs", "crates/frob-worktree/tests/claim_hold.rs", "changelog.d/01M5E0F8MC9XT2PCCB9XG6E8X3.added.md"]
+++

Prereq of 41AWFVY: claim_hold.rs has pure Hold/Pause types but nothing persists them, and no reclaim timestamp is recorded, so work --next and claim evict cannot compute held_or_paused or since_reclaim_secs. Needs a readable store (lease ops hold/resume/reclaim) reachable from frob-worktree, then wiring in next.rs and claim_evict.rs.
