+++
id = "01M3ZX868H7TQ34ZDPXY13NRRG"
title = "indexes/by-id lookup pages"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 2
parent = "01M3ZX776JJSRQXW8Q0327K9QN"
reporter = "lognd"
created = "2026-10-03T03:34:45Z"
updated = "2026-10-11T21:53:49Z"
idempotency_key = "m2-nav-gen-by-id"
labels = ["milestone:2", "area:navigation"]
scope = ["crates/frob-ledger/src/gen/by_id.rs", "crates/frob-ledger/src/lib.rs", "crates/frob-ledger/src/reindex.rs", "crates/frob-ledger/src/ops.rs", "crates/frob-ledger/src/replay.rs", "crates/frob-ledger/src/gen/mod.rs", "crates/frob-ledger/tests/gen_by_id.rs", "docs/guides/ticket-branch.md", "crates/frob/tests/ticket_reindex.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX85S7ASFGT31GDYMRB5JX"

[[acceptance]]
text = "Given any ticket, when generated, then exactly one by-id page lists it with its current path"
bound = true

[[acceptance]]
text = "Given a moved ticket, when regenerated, then its row shows the new path"
bound = true
+++

Implements navigation.md section 1.

indexes/by-id/<xx>.md split by the two ULID characters after the time part, listing ULID, handle, title and current path.
