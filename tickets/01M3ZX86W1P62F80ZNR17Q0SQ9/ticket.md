+++
id = "01M3ZX86W1P62F80ZNR17Q0SQ9"
title = "TICK008 move-outside-reindex"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M3ZX776JJSRQXW8Q0327K9QN"
reporter = "lognd"
created = "2026-10-03T03:34:45Z"
updated = "2026-10-11T19:35:13Z"
idempotency_key = "m2-nav-tick006"
labels = ["milestone:2", "area:navigation", "creates:crates/frob-ledger/src/moves.rs", "creates:crates/frob/tests/ticket_moves.rs", "creates:crates/gob-mdtest/coverage-allowlist.toml", "creates:crates/frob-ledger/src/rules.rs", "creates:crates/frob-ledger/src/lib.rs", "creates:crates/frob-check/src/product.rs", "creates:docs/reference/rules/TICK008.md", "creates:docs/reference/rules/README.md"]
scope = ["crates/frob-obligations/src/tick_moves.rs", "crates/frob-ledger/src/moves.rs", "crates/frob/tests/ticket_moves.rs", "crates/gob-mdtest/coverage-allowlist.toml", "crates/frob-ledger/src/rules.rs", "crates/frob-ledger/src/lib.rs", "crates/frob-check/src/product.rs", "docs/reference/rules/TICK008.md", "docs/reference/rules/README.md"]

[[links]]
kind = "blocked-by"
target = "01M3ZX85S7ASFGT31GDYMRB5JX"

[[acceptance]]
text = "Given a commit that only adds events and edits frontmatter, when checked, then it does not fire"
bound = true

[[acceptance]]
text = "Given a ledger commit without the trailer that renames a ticket file, when checked, then TICK008 fires"
bound = true
+++

Implements navigation.md section 2.2.

A ledger commit without the trailer may not rename or delete a ticket file or touch an event file it did not add.
