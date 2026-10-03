+++
id = "01M4069R19D2KZENDGEH83JZSW"
title = "[pm] config tables materialized by frob init: pull, ready_min, cycle_days, wip, classes, ready, done"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:12:53Z"
updated = "2026-10-03T10:51:29Z"
idempotency_key = "m2-rel-pm-knobs"
labels = ["milestone:2", "area:release", "release:0.532.0"]
scope = ["crates/frob-pm/src/config.rs", "crates/frob/src/init.rs", "docs/reference/config/**", "crates/frob-pm/Cargo.toml", "crates/frob-pm/src/lib.rs", "crates/frob-pm/tests/config.rs", "crates/frob/src/config.rs", "crates/frob/tests/cli.rs", "crates/frob/tests/snapshots/cli__*", "docs/reference/config.md", "docs/schemas/config.json", "frob.toml", "crates/frob/tests/pm_config.rs"]

[[links]]
kind = "blocked-by"
target = "01M4069QWSJEH5KW8K0YR8CA0D"

[[acceptance]]
text = "Given a fresh repository, when frob init runs, then frob.toml carries every [pm] knob with its default and a doc comment"
bound = true

[[acceptance]]
text = "Given an unknown [pm] key, when config loads, then it is reported with a did-you-mean"
bound = false
+++

Declare the [pm], [pm.wip], [pm.classes], [pm.ready] and [pm.done] tables of releases.md 2 and pm-enforcement.md 3 as ConfigTables with defaults and doc comments; frob init writes every knob (no silent inheritance). In this repository frob.toml sets [pm.wip] in_progress = 2.
