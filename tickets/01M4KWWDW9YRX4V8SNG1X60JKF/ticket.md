+++
id = "01M4KWWDW9YRX4V8SNG1X60JKF"
title = "gob-dev profile.toml has no scenario or skip reason for frob ticket closeout"
type = "bug"
category = "todo"
priority = "medium"
reporter = "Claude"
created = "2026-10-10T21:53:08Z"
updated = "2026-10-10T21:53:08Z"
scope = ["crates/gob-dev/**"]

[[acceptance]]
text = "Given the closeout verb, when gob-dev profile_coverage runs, then every_leaf_command_has_a_scenario_or_a_skip_reason passes"
bound = false
+++

found while working ~C8N7M9Q: gob-dev::profile_coverage every_leaf_command_has_a_scenario_or_a_skip_reason fails on experimental: leaf commands with no scenario and no skip reason: frob ticket closeout
