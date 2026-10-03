+++
id = "01M3ZX82TWWY2616S1Q5N48KNK"
title = "Index, fold and merge driver read the new layout through ULIDs, never paths"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T03:34:41Z"
updated = "2026-10-03T03:34:41Z"
idempotency_key = "m2-tb-layout-read"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-ledger/src/index.rs", "crates/frob-ledger/src/fold.rs", "crates/frob-ledger/src/merge.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX82Q2N145P3DWVVY4E868"

[[acceptance]]
text = "Given a ticket file moved to another directory by a reindex, when `ticket show <id>` runs, then it resolves the same ticket and the frontmatter equals the fold of events"
bound = false

[[acceptance]]
text = "Given two branches that each add events to one ticket, when merged, then the driver unions events and refolds"
bound = false
+++

Implements mirror.md section 1; navigation.md section 1.

frob resolves ids through its index; moved or renamed files resolve identically; merge driver unions events and re-folds in the new layout.
