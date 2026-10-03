+++
id = "01M4052R0DZK01W7K8EE77637T"
title = "GitHub reads: issue state, history after an event id, creation revision of the body"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T05:51:35Z"
updated = "2026-10-03T05:51:35Z"
idempotency_key = "m2-mirror2-gh-history-reads"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-gh/src/history.rs", "crates/frob-mirror/src/github/read.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX8182AHQF2XB4WYNC30Q8"

[[links]]
kind = "blocked-by"
target = "01M3ZX83AB2JADBKWFA9SY4J60"

[[links]]
kind = "blocked-by"
target = "01M4052QNSFSWV0SQ0A05XQ12K"

[[acceptance]]
text = "Given an issue with timeline events and body edits, when history after event id E is read, then entries after E arrive in order with actor user id, field, value digest and event id"
bound = false

[[acceptance]]
text = "Given a body edited by a human after creation, when the creation revision is read, then it is the first revision with its author id regardless of later edits"
bound = false

[[acceptance]]
text = "Given more than 99 body edits or deleted revision content, when history is read, then the result carries fidelity gap and does not fail"
bound = false
+++

Implements mirror.md sections 3.3 and 3.4 (history, creation revision, fidelity).

Read one issue's current values, its timeline and body edit history after a given tracker event id (entries carry actor user id, field, value digest, event id), and the creation revision of the body (first revision and its author id). Where GitHub retains only the original body plus the latest 99 edits or revision content was deleted, report fidelity gap rather than failing.
