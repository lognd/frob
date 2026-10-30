+++
id = "01M5XMJJHNP9GEX18NSBZF44PC"
title = "Adopt baseline and Error-only severity in grimble and crunk"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M5XETK612GJ5QZZZXBA6CSGY"
reporter = "lognd"
created = "2026-10-27T02:56:03Z"
updated = "2026-10-30T22:27:51Z"
labels = ["no-story"]
scope = ["crates/grimble-check/**", "crates/crunk-check/**", "docs/design/rules.md", "crates/gob-rules/src/baseline.rs", "docs/reference/config.md", "docs/schemas/config.json", "crates/frob-pm/**"]

[[acceptance]]
text = "grimble and crunk read frob-baseline.toml under their namespaces and drop per-product ramp calls"
bound = true

[[acceptance]]
text = "pm strict and grimble strict knobs are deprecated no-ops"
bound = true
+++

Implements docs/design/rules.md section 6.1 (rules.md 6.1.6). Filed from ~ZHW5Y2M.

no-story: internal engineering task in grimble-check; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
