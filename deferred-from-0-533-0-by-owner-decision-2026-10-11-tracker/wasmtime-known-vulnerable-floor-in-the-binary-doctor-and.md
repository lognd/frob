+++
id = "01M3ZX7WZPVXWM8EYDT3SP89GX"
title = "wasmtime known-vulnerable floor in the binary; doctor and daily summary warning"
type = "task"
category = "todo"
priority = "low"
points = 2
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:35Z"
updated = "2026-10-28T12:55:41Z"
idempotency_key = "m2-sec-wasmtime-floor"
labels = ["milestone:2", "area:security", "no-story"]
scope = ["crates/gob-wasm/src/floor.rs", "crates/frob/src/doctor.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7SCND92D383E8X9CEWJ7"

[[acceptance]]
text = "Given a binary older than the floor with a tier-3 pack, when doctor runs, then it reports the outdated wasmtime"
bound = false

[[acceptance]]
text = "Given two runs on one day, when the summary renders, then the warning appears once"
bound = false
+++

Implements security.md section 2.5 (last bullet).

A floor version compiled in; doctor says so, and at most once a day the summary does when tier 3 runs on an outdated binary.

no-story: internal engineering task in gob-wasm; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
