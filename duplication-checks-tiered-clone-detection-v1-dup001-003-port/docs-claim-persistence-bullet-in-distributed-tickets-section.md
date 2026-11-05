+++
id = "01M6PADYNEBH5VQJVFJN40TDMC"
title = "docs: claim persistence bullet in distributed-tickets section 4.7"
type = "docs"
category = "in-progress"
priority = "medium"
points = 1
parent = "01M4P0SQC82NJ7DV5BC3CAR5Y4"
reporter = "lognd"
created = "2026-11-05T16:59:46Z"
updated = "2026-11-05T17:06:49Z"
labels = ["no-story", "good-first"]
scope = ["docs/design/frob/distributed-tickets.md"]

[[acceptance]]
text = "Given section 4.7 of distributed-tickets.md, when a reader looks for claim notices, then a bullet states that idle claims warn the holder at the end of work --next and show on board and doable"
bound = false
+++

Document the idle-claim notices landed in YFFQSVP and AQ9F2RW.

## Start here

- Files to read first: crates/frob-worktree/src/claim_notice.rs
- Test command: frob check --files docs/design/frob/distributed-tickets.md
- Who to ask: lognd
