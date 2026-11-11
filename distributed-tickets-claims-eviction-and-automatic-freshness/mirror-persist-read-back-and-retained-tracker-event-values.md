+++
id = "01M5EKM08ZM45RZ1JBHC68F156"
title = "mirror: persist read-back and retained tracker event values in the map shard"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-21T06:50:44Z"
updated = "2026-11-11T21:07:55Z"
scope = ["crates/frob-ledger/**", "crates/frob-mirror/**", "docs/**"]

[[acceptance]]
text = "LedgerTickets::state returns the persisted read-back and retained tracker event values from the map shard"
bound = true
+++

found while working ~ACC0466: LedgerTickets::state returns an empty ReadBack and no event_values because the shard carries neither
