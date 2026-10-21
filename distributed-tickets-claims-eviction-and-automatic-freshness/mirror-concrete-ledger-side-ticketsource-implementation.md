+++
id = "01M5EBMAWCRQ2S1GGPYACC0466"
title = "mirror: concrete ledger-side TicketSource implementation"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-21T04:31:07Z"
updated = "2026-10-21T07:11:18Z"
scope = ["crates/frob-mirror/src/ledger_source.rs", "crates/frob-mirror/src/lib.rs", "crates/frob-mirror/Cargo.toml", "crates/frob-mirror/tests/ledger_source.rs", "changelog.d/01M5EBMAWCRQ2S1GGPYACC0466.added.md", "Cargo.lock"]

[[acceptance]]
text = "Given a ledger with mapped and unmapped tickets, when LedgerTickets is read and written as a TicketSource, then it lists, projects, reconciles and records proposals against the real ledger"
bound = true
+++

only the seam trait exists in host.rs. found while working R2MH98S
