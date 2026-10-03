+++
id = "01M4052RW8F31VNBZ6AJM20TF3"
title = "Work classes in strict priority with round-robin resumption inside a class"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T05:51:36Z"
updated = "2026-10-03T05:51:36Z"
idempotency_key = "m2-mirror2-work-classes"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/src/plan.rs"]

[[links]]
kind = "blocked-by"
target = "01M4052RRC7X5Y23PNBDKR9V6W"

[[acceptance]]
text = "Given work in all five classes and a budget for part of it, when planned, then class 1 is exhausted before class 2 and so on"
bound = false

[[acceptance]]
text = "Given two tickets and a budget of 4 calls per run, when runs repeat, then both tickets complete (the F8 trace no longer starves ticket 2)"
bound = false

[[acceptance]]
text = "Given a run that completed ticket T in a class, when the next run starts, then the class resumes after T"
bound = false
+++

Implements mirror.md section 3.2 (work classes; F8).

Strict priority: (1) recovery of uncertain creates, (2) ledger-driven updates oldest first, (3) creates oldest first, (4) reconcile of changed issues, (5) the sweep. Within a class a run resumes after the last completed ticket, never from a fixed order, so no ticket starves.
