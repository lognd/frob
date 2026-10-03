+++
id = "01M40T3VS6VVN80SP39XGS6PK2"
title = "PROC001 (frob's own spawn policy) fires in consumer repositories, and on std::process::ExitCode"
type = "bug"
category = "in-progress"
priority = "high"
points = 2
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T11:59:12Z"
updated = "2026-10-03T12:27:41Z"
idempotency_key = "m2-rel-proc001-repo-local"
labels = ["milestone:2", "area:release", "release:0.532.0"]
scope = ["crates/frob-check/**", "crates/frob-obligations/**", "frob.toml", "docs/reference/rules/**", "crates/gob-exec/src/proc001.rs"]

[[acceptance]]
text = "Given a consumer repository using std::process::ExitCode and Command, when frob check runs, then no PROC001 finding appears"
bound = false

[[acceptance]]
text = "Given this repository, when a crate other than gob-exec or gob-git uses std::process::Command, then PROC001 still fires, and ExitCode alone does not"
bound = false
+++

Reported from the cloc repository (FROB_FEEDBACK.md item 2): PROC001 'uses the process API outside gob-exec and gob-git' fires as a universal Error in a consumer repository, on use std::process::ExitCode, which is not a spawn. The rule encodes this repository's own architecture (only gob-exec and gob-git spawn), so it must be a repo-local rule of the frob repository (declared in this repository's frob.toml or as a frob-repo pack), not a built-in that consumers inherit; and even here it must only match spawning APIs (Command, Child, exec, spawn), not ExitCode, exit or id. Tests: a consumer repository with ExitCode and Command: no PROC001; this repository: still enforced on Command outside the two crates, not on ExitCode.
