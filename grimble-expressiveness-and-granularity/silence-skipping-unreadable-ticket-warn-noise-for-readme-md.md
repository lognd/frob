+++
id = "01M6BNZXB3Y2G94SGFX78K70J0"
title = "Silence skipping-unreadable-ticket WARN noise for README.md and indexes in the ledger"
type = "bug"
category = "in-progress"
priority = "low"
points = 2
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-01T13:50:10Z"
updated = "2026-11-01T22:09:01Z"
scope = ["crates/frob-ledger/src/layout.rs", "changelog.d/01M6BNZXB3Y2G94SGFX78K70J0.fixed.md"]

[[acceptance]]
text = "Indexing skips non-ticket files in the tickets dir without warning; test"
bound = true
+++
