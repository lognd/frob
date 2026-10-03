+++
id = "01M4052SQS2X5XYN24DE9ENQF8"
title = "History cursor as an event id: taken before listing, advanced only after proposals are committed"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T05:51:37Z"
updated = "2026-10-03T05:51:37Z"
idempotency_key = "m2-mirror2-cursor"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/src/cursor.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX83J29R620BVRAVK5Z6DZ"

[[links]]
kind = "blocked-by"
target = "01M4052R0DZK01W7K8EE77637T"

[[acceptance]]
text = "Given a ticket's first read, when processed, then the cursor is taken before its issues are listed and survives a create"
bound = false

[[acceptance]]
text = "Given a crash after proposals are recorded and before their commit, when the run repeats, then the cursor has not advanced and nothing is recorded twice"
bound = false

[[acceptance]]
text = "Given a human edit between the mirror's read and its write, when the next run reads, then the edit lies after the cursor and is read"
bound = false
+++

Implements mirror.md sections 3.3 (F3) and 3.4 (F2, MIR-AUD-25).

The cursor is the history position actually read, a tracker event id and never a time (a newtype so a time cannot be stored). It is taken before the ticket's issues are listed, kept across a create, and advanced only after the proposals it covers are committed.
