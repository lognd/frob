+++
id = "01M5WJKHJK4DD8NP1FTYWF1B8K"
title = "crunk.toml should accept a [rules] table so the release ramp can be turned off"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-26T17:02:23Z"
updated = "2026-10-26T21:21:11Z"
scope = ["crates/crunk-spec/**", "crates/crunk-check/**"]

[[acceptance]]
text = "Given crunk.toml with [rules] ramp = false, when crunk check runs, then new-in-release rules are not downgraded to warn; a [rules] table loads without error"
bound = false
+++

found while working ~B3EMY2Z: crunk.toml rejects [rules] (OWN_TABLES in crunk-spec load.rs), so [rules] ramp = false has no effect for crunk.
