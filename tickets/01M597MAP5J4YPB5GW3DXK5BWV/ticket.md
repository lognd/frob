+++
id = "01M597MAP5J4YPB5GW3DXK5BWV"
title = "Base CI red: crunk-fix missing from ci.yml crunk job, layer table, profile.toml"
type = "bug"
category = "in-progress"
priority = "high"
points = 1
reporter = "lognd"
created = "2026-10-19T04:45:00Z"
updated = "2026-10-19T04:57:54Z"
scope = [".github/workflows/ci.yml", "crates/gob-dev/tests/layering.rs", "crates/gob-dev/profile.toml", "crates/gob-dev/src/**", "docs/design/boundaries.md"]

[[acceptance]]
text = "gob-dev tests ci_plan, layering, profile_coverage pass; cargo dev profile has a crunk fix scenario or skip reason"
bound = false
+++
