+++
id = "01M5H85DZ6NF1Y2DACWGQ3NZVK"
title = "profile: ticket reindex warm median 2025ms exceeds 1000ms budget"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-22T07:28:16Z"
updated = "2026-10-22T07:28:16Z"
scope = ["crates/frob-ledger/src/reindex.rs"]
+++

Found while working ~M7F4X3Q: profile command-budgets test; reindex cost scales with ledger size, no cheap fix identified, needs profiling.
