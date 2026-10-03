+++
id = "01M4052S04N2E2A08NNPAZKPYT"
title = "Round-robin sweep: reconcile the next K issues of a persisted cursor"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T05:51:36Z"
updated = "2026-10-03T05:51:36Z"
idempotency_key = "m2-mirror2-sweep"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/src/sweep.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX83J29R620BVRAVK5Z6DZ"

[[links]]
kind = "blocked-by"
target = "01M4052RW8F31VNBZ6AJM20TF3"

[[acceptance]]
text = "Given N issues and K per run and a feed that reports nothing, when runs repeat, then every issue is visited within ceil(N/K) runs"
bound = false

[[acceptance]]
text = "Given a run stopped midway, when the next run starts, then the sweep resumes after the last completed issue"
bound = false
+++

Implements mirror.md section 3.2 (Sweep).

Each run reconciles the next K issues of a persisted round-robin cursor so every issue is visited within ceil(N/K) runs even when the feed misses a change (repository-level renames do not bump update times).
