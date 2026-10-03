+++
id = "01M4052SVV8ZVVX0AW4MN0Q367"
title = "Read-time capture, fidelity gap and the gap listing"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T05:51:37Z"
updated = "2026-10-03T05:51:37Z"
idempotency_key = "m2-mirror2-capture"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/src/capture.rs"]

[[links]]
kind = "blocked-by"
target = "01M4052R0DZK01W7K8EE77637T"

[[links]]
kind = "blocked-by"
target = "01M4052SQS2X5XYN24DE9ENQF8"

[[acceptance]]
text = "Given a field whose current value differs from the last observed value and no history entry explains it, when read, then it is captured with fidelity gap"
bound = false

[[acceptance]]
text = "Given history beyond the retained window, when read, then the gap is recorded and appears in the gap listing"
bound = false

[[acceptance]]
text = "Given a field changed twice between runs with history retained, when read, then both values and their authors are captured"
bound = false
+++

Implements mirror.md section 3.4 (what nothing is lost means).

The value present at read time is always captured by comparing it with the last observed value; intermediate values and authors come from history while it retains them. Cases with no per-issue history (repository-level renames, project fields other than status, deletions, history beyond retention) are recorded with fidelity = gap and listed for mirror status.
