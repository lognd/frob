+++
id = "01M3ZX86W1P62F80ZNR17Q0SQ9"
title = "TICK006 move-outside-reindex"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M3ZX776JJSRQXW8Q0327K9QN"
reporter = "lognd"
created = "2026-10-03T03:34:45Z"
updated = "2026-10-03T03:34:45Z"
idempotency_key = "m2-nav-tick006"
labels = ["milestone:2", "area:navigation"]
scope = ["crates/frob-obligations/src/tick_moves.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX85S7ASFGT31GDYMRB5JX"

[[acceptance]]
text = "Given a ledger commit without the trailer that renames a ticket file, when checked, then TICK006 fires"
bound = false

[[acceptance]]
text = "Given a commit that only adds events and edits frontmatter, when checked, then it does not fire"
bound = false
+++

Implements navigation.md section 2.2.

A ledger commit without the trailer may not rename or delete a ticket file or touch an event file it did not add.
