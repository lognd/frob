+++
id = "01M4052S40VQGKG930DZPSM01K"
title = "Writer lock and watermark of the last processed ledger commit"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T05:51:36Z"
updated = "2026-10-03T05:51:36Z"
idempotency_key = "m2-mirror2-lock"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/src/lock.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX8141MTBF6G2E6BAD33TS"

[[links]]
kind = "blocked-by"
target = "01M3ZX83J29R620BVRAVK5Z6DZ"

[[acceptance]]
text = "Given a lock held by a live run, when a second run starts, then it exits without work and without error"
bound = false

[[acceptance]]
text = "Given a stale lock past its timeout, when a run starts, then it takes the lock by CAS and logs the takeover"
bound = false

[[acceptance]]
text = "Given a watermark, when a run starts, then only ledger commits after it are processed and the mirror's own commits do not start a run"
bound = false
+++

Implements mirror.md section 3.1 (One writer; MIR-AUD-13).

The job takes a writer lock, a ref on the ticket branch updated by CAS, and keeps a watermark of the last processed ledger commit. The mirror's own ledger commits never trigger runs.
