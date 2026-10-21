+++
id = "01M5G2WH1J8G8WR3PGF5N3TAQD"
title = "Fix snapshots and fixpoint run for gob-config CFG001"
type = "task"
category = "todo"
priority = "medium"
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-21T20:36:47Z"
updated = "2026-10-21T20:36:47Z"
idempotency_key = "g4w-cfg001"
scope = ["crates/gob-config/**"]

[[acceptance]]
text = "CFG001 has a fix fixture, a diff snapshot, and passes the fixpoint harness"
bound = false
+++

Follow-up of ~G4WAFJT: wire the gob-fix harness (gob_fix::run_fixture) for these fixable rules: a fixture per rule, an observe closure over the real check pipeline, an insta snapshot of Outcome::snapshot_text, and missing_fixtures over the registry's Deterministic rules.
