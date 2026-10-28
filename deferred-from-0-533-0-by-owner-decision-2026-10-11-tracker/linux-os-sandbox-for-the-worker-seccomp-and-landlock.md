+++
id = "01M3ZX7W2YAJGB2MCMWDPEDK62"
title = "Linux OS sandbox for the worker: seccomp and Landlock"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:34Z"
updated = "2026-10-28T12:55:51Z"
idempotency_key = "m2-sec-sandbox-linux"
labels = ["milestone:2", "area:security", "no-story"]
scope = ["crates/gob-wasm/src/worker/linux.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7S5JYVCTRD0ZYC57GJ93"

[[acceptance]]
text = "Given the sandboxed worker, when guest-controlled code attempts open() or connect(), then the syscall fails"
bound = false

[[acceptance]]
text = "Given a kernel without Landlock, when the worker starts, then doctor reports the degraded sandbox and the pack is Unresolved if the repository marked it required"
bound = false
+++

Implements security.md section 2.5.

No file access and no network from the worker; defence in depth assumes wasmtime escapes will happen.

no-story: internal engineering task in gob-wasm; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
