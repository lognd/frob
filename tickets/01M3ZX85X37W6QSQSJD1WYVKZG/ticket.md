+++
id = "01M3ZX85X37W6QSQSJD1WYVKZG"
title = "frob ticket reindex [--check] [--code-readme]: decision and reindex commits"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M3ZX776JJSRQXW8Q0327K9QN"
reporter = "lognd"
created = "2026-10-03T03:34:44Z"
updated = "2026-10-03T03:34:44Z"
idempotency_key = "m2-nav-reindex-verb"
labels = ["milestone:2", "area:navigation"]
scope = ["crates/frob/src/ticket/reindex_cmd.rs", "crates/frob-ledger/src/ops.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX85S7ASFGT31GDYMRB5JX"

[[acceptance]]
text = "Given `ticket update --parent`, when run, then two commits result and the second carries the Frob-Reindex trailer"
bound = false

[[acceptance]]
text = "Given `ticket reindex --check`, when the tree is current, then it exits 0 and prints nothing; when stale it prints the diff and exits 1"
bound = false
+++

Implements navigation.md section 2.2.

A parent or title change is two commits written together: the decision commit (event and refolded frontmatter, no moves) and the reindex commit `tickets(reindex): after <event ULID>` with trailer Frob-Reindex: <frob version>; [tickets] index_writer = ci defers the second to CI.
