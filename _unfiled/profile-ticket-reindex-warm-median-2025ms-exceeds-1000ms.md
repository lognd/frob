+++
id = "01M5H85DZ6NF1Y2DACWGQ3NZVK"
title = "profile: ticket reindex warm median 2025ms exceeds 1000ms budget"
type = "bug"
category = "in-progress"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-22T07:28:16Z"
updated = "2026-10-22T18:08:38Z"
scope = ["crates/frob-ledger/src/reindex.rs"]

[[acceptance]]
text = "Given the profile command-budgets test, when ticket reindex runs warm, then median time is under the 1000ms budget"
bound = true

[[acceptance]]
text = "A profile of reindex identifies the dominant cost and the fix is recorded in the ticket"
bound = true
+++

Found while working ~M7F4X3Q: profile command-budgets test; reindex cost scales with ledger size, no cheap fix identified, needs profiling.
