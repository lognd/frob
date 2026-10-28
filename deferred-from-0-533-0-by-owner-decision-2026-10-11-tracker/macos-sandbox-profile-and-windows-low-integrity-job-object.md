+++
id = "01M3ZX7W6XTTCZHQQHA7B8MK76"
title = "macOS sandbox profile and Windows low-integrity job object for the worker"
type = "task"
category = "todo"
priority = "low"
points = 5
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:34Z"
updated = "2026-10-28T12:55:45Z"
idempotency_key = "m2-sec-sandbox-other"
labels = ["milestone:2", "area:security", "no-story"]
scope = ["crates/gob-wasm/src/worker/macos.rs", "crates/gob-wasm/src/worker/windows.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7S5JYVCTRD0ZYC57GJ93"

[[acceptance]]
text = "Given the macOS worker, when it tries to open a file, then the profile denies it"
bound = false

[[acceptance]]
text = "Given the Windows worker, when it starts, then it runs in a job object at low integrity"
bound = false
+++

Implements security.md section 2.5.

Where available; absent platforms report the degraded sandbox.

no-story: internal engineering task in gob-wasm; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
