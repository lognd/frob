+++
id = "01M4052RMBKXD6T8ANNFWJ751M"
title = "Write journal and own-write attribution"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T05:51:36Z"
updated = "2026-10-03T05:51:36Z"
idempotency_key = "m2-mirror2-journal"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/src/journal.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX83AB2JADBKWFA9SY4J60"

[[links]]
kind = "blocked-by"
target = "01M3ZX83J29R620BVRAVK5Z6DZ"

[[acceptance]]
text = "Given a mutation about to be sent, when journaled, then (issue, field, value digest, run id) is recorded before the call is made"
bound = false

[[acceptance]]
text = "Given a history entry by a bot id whose digest matches a journaled write, when classified, then it is own; given a bot-id entry with no match, then it is an edit by unknown automation"
bound = false

[[acceptance]]
text = "Given unconfirmed journal entries at run start, when the run begins, then they are re-read first and each is confirmed or marked lost"
bound = false
+++

Implements mirror.md section 3.3 (Own writes).

Before each mutation the run journals (issue, field, value digest, run id); a history entry is own only if its actor is a bot id and its value digest matches a journaled write; any other bot entry is an edit by unknown automation. Unconfirmed entries are re-read at the start of the next run.
