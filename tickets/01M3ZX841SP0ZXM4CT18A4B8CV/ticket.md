+++
id = "01M3ZX841SP0ZXM4CT18A4B8CV"
title = "Outbox: idempotent operations, incremental sync, full resync verb"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T03:34:43Z"
updated = "2026-10-03T03:34:43Z"
idempotency_key = "m2-mirror-outbox"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/src/outbox.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX83J29R620BVRAVK5Z6DZ"

[[links]]
kind = "blocked-by"
target = "01M3ZX83XX6D2N7XDTVRVYV6TS"

[[acceptance]]
text = "Given a run interrupted after two of five operations, when rerun, then only the remaining three execute and nothing is duplicated"
bound = false

[[acceptance]]
text = "Given no new events, when the mirror runs, then no tracker request that mutates state is made"
bound = false
+++

Implements mirror.md section 3 (partial failure, rate limits).

Each ledger event needing publishing becomes an operation keyed by ticket ULID plus event ULID; an operation whose hash matches the tracker's current state is skipped; failures retry next run; incremental by default.
