+++
id = "01M59RWT16TFNSACMMTTXX200T"
title = "G14b: grimble-capabilities: wire the matrix into grimble-bind, excuses, CAP001-002 via the crate, census"
type = "task"
category = "in-progress"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-10-19T09:46:43Z"
updated = "2026-10-19T14:03:51Z"
scope = ["crates/grimble-capabilities/**", "crates/grimble-bind/src/caps.rs", "crates/grimble-bind/Cargo.toml", "Cargo.lock", "docs/design/packs.md", "docs/design/grimble-model.md"]
+++

Follow-up of ~V56RXG4: the crate holds the cell computation only. Remaining: derive NodeInput from observed uses in grimble-bind, move CAP001/CAP002 emission onto the matrix, template excuses and CAP004, Bounds-aware uses, matrix output and census.
