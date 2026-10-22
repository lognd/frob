+++
id = "01M5GVQ4JMBG1CC0G6RBS28E9V"
title = "gob-plan: versioned grimble-check dev-dependency closes a publish cycle"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-22T03:50:45Z"
updated = "2026-10-22T04:51:44Z"
scope = ["crates/gob-plan/Cargo.toml"]

[[acceptance]]
text = "gob-dev publish plan of this workspace has no dependency cycle (both publish::tests workspace tests pass)"
bound = true
+++

gob-plan dev-depends on grimble-check with a version, but grimble-check depends on gob-plan, so the publish order sees gob-plan <-> grimble-check and gob-dev publish::tests::this_workspace_reads_and_plans_without_a_cycle and ::crates_with_no_consumer_are_skipped_and_no_published_crate_needs_a_skipped_one fail in nextest (CI would fail once clippy passes). Make the dev-dependency path-only like gob-macros so cargo strips it from the packaged manifest.
