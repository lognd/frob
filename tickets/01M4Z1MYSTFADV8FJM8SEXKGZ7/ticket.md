+++
id = "01M4Z1MYSTFADV8FJM8SEXKGZ7"
title = "Land train: train state schema under .git/frob/train and its store"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M4Z1KTKEVF53GWM6ZN7PFN4Q"
reporter = "lognd"
created = "2026-10-15T05:48:05Z"
updated = "2026-10-15T05:48:05Z"
idempotency_key = "train-state"
labels = ["area:land"]
scope = ["crates/frob-land/src/train_state.rs"]

[[acceptance]]
text = "Given a written state, when reloaded, then it round-trips and validates against its schema"
bound = false

[[acceptance]]
text = "Given a crashed driver, when status runs, then the stale train is reported and resumable"
bound = false
+++

Pydantic-equivalent serde+schemars structs for queue, current train, per-candidate result and batch-size state, stored as JSON under .git/frob/train with atomic write and the existing lockfile helper. Crash-safe resume: a stale train is detected by pid/start like land.lock.holder. Dead-holder recovery logged.
