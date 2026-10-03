+++
id = "01M3ZX82K7HX9D2VKT25KS4MV2"
title = "Ticket path function: top-epic directory, EPIC.md, _unfiled, collisions"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M3ZX776JJSRQXW8Q0327K9QN"
reporter = "lognd"
created = "2026-10-03T03:34:41Z"
updated = "2026-10-03T03:34:41Z"
idempotency_key = "m2-nav-path"
labels = ["milestone:2", "area:navigation", "good-first"]
scope = ["crates/frob-ledger/src/path_fn.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX82FBZHFCX6P69NRTFCH7"

[[acceptance]]
text = "Given a ticket under a sub-epic of epic `parser-rewrite`, when pathed, then it is `parser-rewrite/<slug>.md` with no sub-epic directory"
bound = false

[[acceptance]]
text = "Given two tickets in one directory with the same slug, when pathed in either creation order, then both get -<handle> and the paths are identical across orders"
bound = false
+++

Implements navigation.md section 2.1.

path = <top-epic-slug>/<ticket-slug>.md with sub-epics flattened; epic ticket is EPIC.md; no epic is _unfiled/; two tickets with one slug in a directory both get -<handle> appended, independent of creation order.

## Start here
Read navigation.md section 2.1 and crates/frob-ledger/src/slug.rs (from nav-slug). Test: `cargo nextest run -p frob-ledger`. Ask: the repository owner (Logan) in a comment on this ticket.
