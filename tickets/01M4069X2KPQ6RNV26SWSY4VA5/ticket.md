+++
id = "01M4069X2KPQ6RNV26SWSY4VA5"
title = "Lockstep version bump across Cargo workspace and wheel metadata"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:12:58Z"
updated = "2026-10-03T08:16:41Z"
idempotency_key = "m2-rel-version-bump"
labels = ["milestone:2", "area:release", "release:0.532.0"]
scope = ["crates/frob-release/src/bump.rs", "crates/frob-release/Cargo.toml", "crates/frob-release/src/lib.rs", "crates/frob-release/src/rel002.rs", "crates/frob-release/src/error.rs", "crates/frob-release/tests/bump.rs"]

[[links]]
kind = "blocked-by"
target = "01M4069WNGJ8YR9DTTM9K9K8V5"

[[acceptance]]
text = "Given a workspace at 0.0.0, when bump 0.532.0 runs, then every crate and the wheel metadata read 0.532.0 and Cargo.lock updates"
bound = false

[[acceptance]]
text = "Given the same version again, when bump runs, then no file changes"
bound = false
+++

A function and `frob release bump VERSION --dry-run` that rewrites [workspace.package] version, intra-workspace dependency version pins and the wheel's pyproject version with format-preserving TOML edits, then re-checks REL002; idempotent.
