+++
id = "01M3ZX85S7ASFGT31GDYMRB5JX"
title = "Reindex function: move files to computed paths and render the generated set in memory"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M3ZX776JJSRQXW8Q0327K9QN"
reporter = "lognd"
created = "2026-10-03T03:34:44Z"
updated = "2026-10-03T03:34:44Z"
idempotency_key = "m2-nav-reindex-fn"
labels = ["milestone:2", "area:navigation"]
scope = ["crates/frob-ledger/src/reindex.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX82K7HX9D2VKT25KS4MV2"

[[links]]
kind = "blocked-by"
target = "01M3ZX82Q2N145P3DWVVY4E868"

[[links]]
kind = "blocked-by"
target = "01M3ZX85N2KZ39PG65MX0YT2P0"

[[acceptance]]
text = "Given a ticket whose title changed, when reindexed, then its file is renamed to the new slug with an identical blob id and nothing else moves"
bound = false

[[acceptance]]
text = "Given the same tree and version, when reindexed twice, then the output tree ids are equal"
bound = false
+++

Implements navigation.md sections 2.2 and 3.

Pure function of ledger tree plus frob version: no timestamps (an as-of event ULID line), stable order, capped pages; a moved ticket keeps its blob id.
