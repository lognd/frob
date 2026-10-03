+++
id = "01M4052SBZCJ3MRHGTPAFW4QP1"
title = "Duplicate closing on every run"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T05:51:36Z"
updated = "2026-10-03T05:51:36Z"
idempotency_key = "m2-mirror2-dups"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/src/dups.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX851JW2KYRMCCK5RQKG5W"

[[links]]
kind = "blocked-by"
target = "01M4052QWSEERAG3JPCGXM4RK4"

[[links]]
kind = "blocked-by"
target = "01M4052R0DZK01W7K8EE77637T"

[[links]]
kind = "blocked-by"
target = "01M4052R88Y0A9HQHDB86ERMEM"

[[acceptance]]
text = "Given two bot issues with valid markers for one ULID, when a run lists them, then the lowest number is canonical and the other is closed as a duplicate of it with its marker kept"
bound = false

[[acceptance]]
text = "Given a closed duplicate that a human edited, when the next run reads it, then the edit is captured"
bound = false

[[acceptance]]
text = "Given a human who reopens a closed duplicate, when the next run lists, then it is closed again"
bound = false
+++

Implements mirror.md section 3.3 (Duplicates; F6).

Every run, if two bot issues carry valid markers for one ULID the lowest issue number is canonical; the others are closed as duplicates of it, keep their markers so they are never re-adopted, and their history is still read so edits made on them are captured.
