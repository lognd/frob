+++
id = "01M5M1TVT09K4YPK17S62Y1A18"
title = "Wire COH003 layers into coh_pass and product so live runs use them"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-23T09:35:21Z"
updated = "2026-10-23T09:57:18Z"
scope = ["crates/grimble-check/**", "docs/design/**", "docs/reference/rules/**", "Cargo.lock", "docs/reference/config.md", "docs/schemas/config.json", "changelog.d/01M5M1TVT09K4YPK17S62Y1A18.changed.md"]

[[acceptance]]
text = "COH003 is registered and runs through coh_pass and product using layers::coh003_options"
bound = true
+++

Follow-up of WXQ03KP: layers.rs fills Coh003Options but no live run consumes it.
