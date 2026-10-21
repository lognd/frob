+++
id = "01M4K8HPJ38DWG338WBP8YV3RW"
title = "frob test and frob land spawn cargo builds that ignore CARGO_PROFILE and CARGO_INCREMENTAL env, filling the disk with debuginfo test binaries"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "Claude"
created = "2026-10-10T15:57:45Z"
updated = "2026-10-21T06:04:40Z"
scope = ["crates/frob-tests/**"]

[[acceptance]]
text = "frob test passes through the caller's CARGO_* profile env to cargo"
bound = true
+++

found while coordinating: with per-command env set, frob test still grew target/debug/deps to 16G; only a user-level cargo config fixed it.
