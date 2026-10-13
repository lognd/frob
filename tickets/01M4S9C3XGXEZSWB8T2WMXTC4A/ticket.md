+++
id = "01M4S9C3XGXEZSWB8T2WMXTC4A"
title = "gob-dev profile: frob lease release has no scenario or skip reason"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "lognd"
created = "2026-10-13T00:07:37Z"
updated = "2026-10-13T03:12:32Z"
scope = ["crates/gob-dev/profile.toml"]

[[acceptance]]
text = "every_leaf_command_has_a_scenario_or_a_skip_reason passes with frob lease release skipped in crates/gob-dev/profile.toml"
bound = true
+++

found while working ~C78QET8: test every_leaf_command_has_a_scenario_or_a_skip_reason (crates/gob-dev/tests/profile_coverage.rs:42) fails on leaf frob lease release
