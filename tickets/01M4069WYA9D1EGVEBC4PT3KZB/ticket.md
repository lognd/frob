+++
id = "01M4069WYA9D1EGVEBC4PT3KZB"
title = "release status: CI green on the tip, via gh with an Unresolved fallback"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:12:58Z"
updated = "2026-10-03T11:51:54Z"
idempotency_key = "m2-rel-release-ci"
labels = ["milestone:2", "area:release", "release:0.532.0"]
scope = ["crates/frob-release/src/ci.rs", "crates/gob-git/src/read.rs", "crates/frob-release/Cargo.toml", "crates/frob-release/src/status.rs", "crates/frob-release/src/lib.rs", "crates/frob-release/src/config.rs", "crates/frob-release/tests/release_workflow.rs", "crates/frob/src/release_cmd.rs"]

[[links]]
kind = "blocked-by"
target = "01M4069WSTV5ZJMRPYR2YECX6Q"

[[acceptance]]
text = "Given recorded check-runs with a failure, when status runs, then CI is reported red"
bound = false

[[acceptance]]
text = "Given gh not installed, when status runs, then CI is Unresolved with the reason"
bound = false
+++

Query the check-runs of the tip commit through `gh api` (argv, no shell, scrubbed environment); not green or gh missing or unauthenticated is Unresolved with the reason, never green by default. A cargo dev test uses recorded fixtures.
