+++
id = "01M5G2WH1J8G8WR3PGF5N3TAQD"
title = "Fix snapshots and fixpoint run for gob-config CFG001"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-21T20:36:47Z"
updated = "2026-10-22T00:51:06Z"
idempotency_key = "g4w-cfg001"
scope = ["crates/gob-config/**", "changelog.d/01M5G2WH1J8G8WR3PGF5N3TAQD.added.md"]

[[acceptance]]
text = "CFG001 has a fix fixture, a diff snapshot, and passes the fixpoint harness"
bound = false

[[acceptance]]
text = "a gob_fix::run_fixture fixture per fixable rule with an insta snapshot and missing_fixtures coverage over the registry"
bound = false

[[acceptance]]
text = "CFG001 partial file gains missing knobs, keeps comments, one-round fixpoint snapshot"
bound = false

[[acceptance]]
text = "CFG001 empty file fixes in one round with diff snapshot"
bound = false

[[acceptance]]
text = "CFG001 complete file is a no-op (zero rounds)"
bound = false

[[acceptance]]
text = "CFG001 fixed output is idempotent (second run zero rounds)"
bound = false
+++

Follow-up of ~G4WAFJT: wire the gob-fix harness (gob_fix::run_fixture) for these fixable rules: a fixture per rule, an observe closure over the real check pipeline, an insta snapshot of Outcome::snapshot_text, and missing_fixtures over the registry's Deterministic rules.
