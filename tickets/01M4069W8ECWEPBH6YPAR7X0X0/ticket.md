+++
id = "01M4069W8ECWEPBH6YPAR7X0X0"
title = "frob release changelog: compile changelog.d fragments into CHANGELOG.md"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:12:57Z"
updated = "2026-10-03T07:41:15Z"
idempotency_key = "m2-rel-changelog-compile"
labels = ["milestone:2", "area:release", "release:0.532.0"]
scope = ["crates/frob-release/**", "Cargo.toml", "changelog.d/.gitkeep", "docs/reference/changelog.md", "CHANGELOG.md", "CHANGELOG-v1.md", "crates/frob/src/release_cmd.rs", "crates/frob/src/lib.rs", "crates/frob/Cargo.toml", "frob.toml", "docs/reference/cli/frob.md", "docs/reference/cli/any.md", "crates/frob/tests/release.rs", "crates/frob/tests/snapshots/**", "Cargo.lock"]

[[links]]
kind = "blocked-by"
target = "01M4069QWSJEH5KW8K0YR8CA0D"

[[acceptance]]
text = "Given fragments for frob and gob, when the compile runs, then CHANGELOG.md gains one version heading grouped by product and type and the fragments are removed"
bound = false

[[acceptance]]
text = "Given a malformed fragment name, when --check runs, then it exits 3 naming the file"
bound = false
+++

New crate frob-release (documentation.md 6). Fragments `changelog.d/<ulid>.<added|changed|fixed|removed|deprecated|security>.md`, first line prefixed with the product; `frob release changelog VERSION [--check|--preview]` compiles per product under one version heading in CHANGELOG.md and deletes the fragments; --check validates shape. This repository's CHANGELOG.md is the v1 history and is excluded from checks, so the compile prepends a v2 section above it (open question recorded in the ticket thread).
