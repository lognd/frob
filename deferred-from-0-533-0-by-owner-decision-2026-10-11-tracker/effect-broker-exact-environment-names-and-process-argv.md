+++
id = "01M3ZX7WQ8ZT5XGC8406Z8K3SJ"
title = "Effect broker: exact environment names and process argv templates"
type = "task"
category = "todo"
priority = "low"
points = 3
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:35Z"
updated = "2026-10-03T03:34:35Z"
idempotency_key = "m2-sec-broker-env"
labels = ["milestone:2", "area:security"]
scope = ["crates/gob-wasm/src/broker/env.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7VPGRERTZNVS5VR437JY"

[[links]]
kind = "blocked-by"
target = "01M3ZX7WAWQ1B4X0FWYCGC4SDH"

[[acceptance]]
text = "Given a grant for RUST_LOG, when the guest asks for HOME, then the answer is denied"
bound = false

[[acceptance]]
text = "Given a granted subprocess template, when the guest passes an arg outside the template, then it is refused"
bound = false
+++

Implements security.md section 2.5 (environment, processes).

Environment answered by exact name from the broker; the worker never sees the real environment; subprocess only via argv templates of 2.4.
