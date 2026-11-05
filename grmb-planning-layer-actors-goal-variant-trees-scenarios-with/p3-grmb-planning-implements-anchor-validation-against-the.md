+++
id = "01M6BYKR12BCNQ3P3BR3J3AR58"
title = "P3 grmb planning: implements anchor validation against the graph export and status overlay"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4FDBDC401KMNN4C12QTA3PK"
reporter = "lognd"
created = "2026-11-01T16:20:49Z"
updated = "2026-11-05T19:27:53Z"
labels = ["grimble", "no-story"]
scope = ["crates/frob-ledger/src/**", "crates/frob-pm/src/fold.rs", "docs/design/tickets.md", "changelog.d/**"]

[[acceptance]]
text = "Given a ticket with implements design:<anchor>, when it is created or checked, then the anchor is validated against the grimble graph export and an unknown anchor is refused"
bound = true

[[acceptance]]
text = "Given a validated implements link, when the overlay is computed, then planned, in-progress, done and the test verdict are overlaid onto the anchor"
bound = false
+++

Child of ~2QTA3PK. Validation and overlay halves of the P3 description. Work no-story: internal engineering task.
