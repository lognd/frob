+++
id = "01M5WJKHJK4DD8NP1FTYWF1B8K"
title = "crunk.toml should accept a [rules] table so the release ramp can be turned off"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-26T17:02:23Z"
updated = "2026-10-26T17:02:23Z"
scope = ["crates/crunk-spec/**"]
+++

found while working ~B3EMY2Z: crunk.toml rejects [rules] (OWN_TABLES in crunk-spec load.rs), so [rules] ramp = false has no effect for crunk.
