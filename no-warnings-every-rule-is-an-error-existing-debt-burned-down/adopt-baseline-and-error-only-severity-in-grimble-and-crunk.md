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
updated = "2026-10-27T02:56:03Z"
scope = ["crates/grimble-check/**"]

[[acceptance]]
text = "grimble and crunk read frob-baseline.toml under their namespaces and drop per-product ramp calls"
bound = false

[[acceptance]]
text = "pm strict and grimble strict knobs are deprecated no-ops"
bound = false
+++

Implements docs/design/rules.md section 6.1 (rules.md 6.1.6). Filed from ~ZHW5Y2M.
