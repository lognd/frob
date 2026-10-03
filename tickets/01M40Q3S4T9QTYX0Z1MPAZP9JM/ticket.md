+++
id = "01M40Q3S4T9QTYX0Z1MPAZP9JM"
title = "Repository WIP check is not atomic with the in-progress transition"
type = "bug"
category = "in-progress"
priority = "low"
points = 2
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T11:06:43Z"
updated = "2026-10-03T17:10:36Z"
idempotency_key = "m2-rel-wip-atomic"
labels = ["milestone:2", "area:release"]
scope = ["crates/frob-worktree/**", "crates/frob-lease/**", "docs/design/tickets.md"]

[[acceptance]]
text = "Given two concurrent work calls racing for the last WIP slot, when both run, then exactly one succeeds and the other exits 3 with E-WIP-REPO"
bound = false
+++

From ~ZERXHAH: two concurrent frob work calls on different tickets can both pass the repository WIP check before either records in-progress. Take the repository count and the transition under one lock (the lease store's lock, or a CAS on the ledger ref that re-checks the count on retry), and test with two threads racing for the last slot.
