+++
id = "01M5G2WH7Q04ERV0MCR8ERTF75"
title = "Fix snapshots and fixpoint run for frob-obligations tick_paths fix"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-21T20:36:47Z"
updated = "2026-10-22T00:51:25Z"
idempotency_key = "g4w-tickpaths"
scope = ["crates/frob-obligations/**", "changelog.d/01M5G2WH7Q04ERV0MCR8ERTF75.added.md"]

[[acceptance]]
text = "the tick_paths fix has a fixture, a diff snapshot, and passes the fixpoint harness"
bound = true

[[acceptance]]
text = "a gob_fix::run_fixture fixture per fixable rule with an insta snapshot and missing_fixtures coverage over the registry"
bound = true

[[acceptance]]
text = "rerunning the tick_paths fix on its own output is a no-op (zero rounds, identical files)"
bound = true

[[acceptance]]
text = "clean and generated text yields no fix rounds and an unchanged tree"
bound = true
+++

Follow-up of ~G4WAFJT: wire the gob-fix harness (gob_fix::run_fixture) for these fixable rules: a fixture per rule, an observe closure over the real check pipeline, an insta snapshot of Outcome::snapshot_text, and missing_fixtures over the registry's Deterministic rules.
