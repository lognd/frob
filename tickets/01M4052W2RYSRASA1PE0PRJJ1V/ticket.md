+++
id = "01M4052W2RYSRASA1PE0PRJJ1V"
title = "Progress commits: sharded map committed every K operations, rate-limited stop"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T05:51:39Z"
updated = "2026-10-03T05:51:39Z"
idempotency_key = "m2-mirror2-progress"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/src/progress.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX83J29R620BVRAVK5Z6DZ"

[[links]]
kind = "blocked-by"
target = "01M4052QNSFSWV0SQ0A05XQ12K"

[[links]]
kind = "blocked-by"
target = "01M4052RRC7X5Y23PNBDKR9V6W"

[[acceptance]]
text = "Given a run stopped by a rate limit, when it ends, then its completed shards are committed and MIR001 rate-limited names the next window"
bound = false

[[acceptance]]
text = "Given a crash after the K-th operation, when the next run starts, then at most K operations are repeated and none is duplicated"
bound = false
+++

Implements mirror.md section 3.2 (Progress; MIR-AUD-14).

A stopped run commits its progress (shards every K operations) and reports MIR001 rate-limited with the next window; the next run continues.
