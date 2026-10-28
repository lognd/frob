+++
id = "01M3ZX7S5JYVCTRD0ZYC57GJ93"
title = "Sandbox worker process: empty environment, one pipe, no secrets"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:31Z"
updated = "2026-10-28T12:55:49Z"
idempotency_key = "m2-sec-sandbox-worker"
labels = ["milestone:2", "area:security", "no-story"]
scope = ["crates/gob-wasm/src/worker/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7S1ZBWEC0PE895ZC6KXN"

[[acceptance]]
text = "Given the worker spawned with a poisoned parent environment, when it inspects its environment, then it is empty"
bound = false

[[acceptance]]
text = "Given the worker, when it lists open descriptors, then only the one pipe is present"
bound = false
+++

Implements security.md section 2.5 (I11).

Separate process for tier-3 components and WASM grammars: empty environment, no inherited descriptors but one pipe, only the WASM features the WIT world needs.

no-story: internal engineering task in gob-wasm; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
