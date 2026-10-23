+++
id = "01M5MDT81QR8F0E67N61AYZDN2"
title = 'Document [check] exclude opt-in ("!dir/") in gob-check config doc comment and single-source crunk NOISE_DIRS with gob-walk GENERATED_DIRS'
type = "task"
category = "todo"
priority = "low"
points = 2
reporter = "lognd"
created = "2026-10-23T13:04:44Z"
updated = "2026-10-23T13:04:44Z"
scope = ["crates/gob-check/src/config.rs", "crates/crunk-ingest/src/walk.rs", "crates/crunk-check/src/review.rs", "changelog.d/**"]

[[acceptance]]
text = "Given the generated config reference, when read, then it documents the opt-in for default-excluded report directories, and crunk walkers use the shared gob-walk list"
bound = false
+++
