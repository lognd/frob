+++
id = "01M4HW9GCNQD67H73H3RNPJCZN"
title = "gob-dev profile_coverage fails on experimental: frob ticket migrate has no scenario or skip reason"
type = "bug"
category = "todo"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-10T03:04:19Z"
updated = "2026-10-10T03:04:19Z"
scope = ["crates/gob-dev/profile.toml"]

[[acceptance]]
text = "Given experimental, when cargo nextest run -p gob-dev runs, then profile_coverage passes"
bound = false
+++

found while working ~HDTYDAJ: cargo nextest run -p gob-dev fails every_leaf_command_has_a_scenario_or_a_skip_reason: leaf commands with no scenario and no skip reason in crates/gob-dev/profile.toml: [frob ticket migrate]. Add a scenario or a skip reason.
