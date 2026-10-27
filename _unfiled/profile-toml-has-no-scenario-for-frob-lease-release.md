+++
id = "01M4SA87AYG9CPN4WVYFXDPWM1"
title = "profile.toml has no scenario for frob lease release"
type = "bug"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-13T00:22:58Z"
updated = "2026-10-27T02:58:18Z"
scope = ["crates/gob-dev/profile.toml"]
+++

found while working ~E9W4M0D: gob-dev test every_leaf_command_has_a_scenario_or_a_skip_reason fails on experimental because frob lease release (registered in crates/frob/src/product.rs) has no scenario or skip reason in crates/gob-dev/profile.toml
