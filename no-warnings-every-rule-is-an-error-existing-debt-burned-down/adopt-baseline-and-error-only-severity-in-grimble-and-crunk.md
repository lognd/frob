+++
id = "01M5XMJJHNP9GEX18NSBZF44PC"
title = "Adopt baseline and Error-only severity in grimble and crunk"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M5XETK612GJ5QZZZXBA6CSGY"
reporter = "lognd"
created = "2026-10-27T02:56:03Z"
updated = "2026-10-28T12:55:49Z"
labels = ["no-story"]
scope = ["crates/grimble-check/**"]

[[acceptance]]
text = "grimble and crunk read frob-baseline.toml under their namespaces and drop per-product ramp calls"
bound = false

[[acceptance]]
text = "pm strict and grimble strict knobs are deprecated no-ops"
bound = false
+++

Implements docs/design/rules.md section 6.1 (rules.md 6.1.6). Filed from ~ZHW5Y2M.

no-story: internal engineering task in grimble-check; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
