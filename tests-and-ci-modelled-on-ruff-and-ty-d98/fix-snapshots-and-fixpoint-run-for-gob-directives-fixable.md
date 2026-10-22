+++
id = "01M5G2WH43B41KTYYK40WS3RZW"
title = "Fix snapshots and fixpoint run for gob-directives fixable rules"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-21T20:36:47Z"
updated = "2026-10-22T00:56:02Z"
idempotency_key = "g4w-directives"
scope = ["crates/gob-directives/**", "changelog.d/01M5G2WH43B41KTYYK40WS3RZW.added.md"]

[[acceptance]]
text = "each Deterministic directive rule has a fix fixture, a diff snapshot, and passes the fixpoint harness"
bound = true

[[acceptance]]
text = "a gob_fix::run_fixture fixture per fixable rule with an insta snapshot and missing_fixtures coverage over the registry"
bound = true

[[acceptance]]
text = "DSL002 v1 keys fix to a fixpoint with a diff snapshot"
bound = true

[[acceptance]]
text = "DSL003 deprecated spellings fix to a fixpoint with a diff snapshot"
bound = true

[[acceptance]]
text = "fixed output is idempotent and leaves no findings"
bound = true

[[acceptance]]
text = "clean input is a no-op"
bound = true

[[acceptance]]
text = "a finding without a mechanical fix is left unchanged"
bound = true

[[acceptance]]
text = "a placeholder fix applies only at a higher tier"
bound = true

[[acceptance]]
text = "every Deterministic registry rule has a fixture (missing_fixtures)"
bound = true

[[acceptance]]
text = "a rule without a fixture is reported by missing_fixtures"
bound = false
+++

Follow-up of ~G4WAFJT: wire the gob-fix harness (gob_fix::run_fixture) for these fixable rules: a fixture per rule, an observe closure over the real check pipeline, an insta snapshot of Outcome::snapshot_text, and missing_fixtures over the registry's Deterministic rules.
