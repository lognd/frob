+++
id = "01M3ZX7RY11A00KAWP8126XSWA"
title = "--timing reports time per pack"
type = "task"
category = "todo"
priority = "low"
points = 2
parent = "01M3ZX76SB6GRNSW6AVFRFVJVQ"
reporter = "lognd"
created = "2026-10-03T03:34:31Z"
updated = "2026-10-03T03:34:31Z"
idempotency_key = "m2-packs-timing"
labels = ["milestone:2", "area:packs"]
scope = ["crates/gob-log/src/**", "crates/gob-check/src/pipeline.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7F1SGDAFM6ZQ8BP7TEN3"

[[links]]
kind = "blocked-by"
target = "01M3ZX7FKFSHB8KZM2N4CNF0P9"

[[acceptance]]
text = "Given a run with std and one plugin pack, when `--timing` is set, then the span tree has one entry per pack with its rule time"
bound = false

[[acceptance]]
text = "Given no plugin, when `--timing` is set, then only std appears"
bound = false
+++

Implements plugins.md section 6.6 (last sentence).

A slow plugin is visible by name in the timing tree.
