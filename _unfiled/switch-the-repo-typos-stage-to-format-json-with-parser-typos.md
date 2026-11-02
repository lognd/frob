+++
id = "01M51B9C3275RDBGRHMGJE53FE"
title = "Switch the repo typos stage to --format json with parser typos-json and keep CI parity green"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-16T03:15:00Z"
updated = "2026-11-02T12:54:23Z"
labels = ["no-story"]
scope = ["frob.toml", "crates/gob-dev/**", "docs/**"]

[[acceptance]]
text = "frob.toml typos stage runs typos --format json with parser typos-json and the gob-dev hygiene test pins both"
bound = false
+++

no-story: internal engineering task in gob-dev; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
