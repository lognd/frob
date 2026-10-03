+++
id = "01M4069Y65FA7GGXG2F6N2KET1"
title = "crates.io publish in dependency order, resumable (cargo dev publish and the job)"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:12:59Z"
updated = "2026-10-03T15:28:35Z"
idempotency_key = "m2-rel-publish-crates"
labels = ["milestone:2", "area:release"]
scope = ["crates/gob-dev/src/publish.rs", ".github/workflows/release.yml", "crates/gob-dev/src/lib.rs", "crates/gob-dev/src/main.rs", "crates/gob-dev/Cargo.toml", "Cargo.lock", "crates/frob-release/tests/release_workflow.rs"]

[[links]]
kind = "blocked-by"
target = "01M4069Y1YR0XCN4BKDDH63PV1"

[[acceptance]]
text = "Given a registry holding the first three crates at the version, when publish runs, then it starts at the fourth in dependency order"
bound = false

[[acceptance]]
text = "Given --dry-run, when publish runs, then it prints the order and publishes nothing"
bound = false
+++

Topologically order the workspace crates from cargo metadata, skip crates whose version already exists on the registry (so a partial publish resumes from the first unpublished crate and never re-bumps), wait for the index between dependents, dry-run mode for CI. The job runs in a protected `crates-io` environment; prefer crates.io trusted publishing (OIDC) over a stored token, else the token lives only in that environment. Open question: crates.io trusted publishing availability for first publish.
