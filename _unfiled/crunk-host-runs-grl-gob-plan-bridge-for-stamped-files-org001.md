+++
id = "01M71T80ZZPW5Z00CKF3ANQ2X3"
title = "crunk host runs GRL: gob-plan bridge for stamped files, ORG001/003/004/005, retire Rust duplicates (follow-up of NBAN5SY)"
type = "task"
category = "in-progress"
priority = "medium"
points = 8
reporter = "lognd"
created = "2026-11-10T04:07:48Z"
updated = "2026-11-10T23:26:47Z"
scope = ["changelog.d/*.added.md", "docs/**", "crates/crunk-rules/src/**", "crates/crunk-rules/tests/**", "crates/crunk-ingest/src/**", "crates/gob-plan/src/**", "crates/gob-plan/tests/**", "crates/crunk-rules/Cargo.toml", "packs/crunk-core/**", "Cargo.lock"]

[[acceptance]]
text = "gob-plan Input/Relations bridge builds file nodes with attrs plus config.layers and config.org tables from StampedFile"
bound = true

[[acceptance]]
text = "generated GRL modules LAYER001 and ORG002 run from the crunk host"
bound = true
+++
