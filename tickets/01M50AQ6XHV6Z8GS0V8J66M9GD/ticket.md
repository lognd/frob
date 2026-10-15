+++
id = "01M50AQ6XHV6Z8GS0V8J66M9GD"
title = "Wire [packs] crunk_web switch into crunk.toml and crunk rule catalog"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-15T17:45:50Z"
updated = "2026-10-15T19:48:45Z"
scope = ["crates/crunk-spec/**", "crates/crunk-cli/**", "crates/crunk/**", "crates/crunk-check/**"]
+++

found while working ~X5W2SPP: crunk_check::packs::PacksSwitch (default off) and packs::catalog() exist; crunk.toml [packs] crunk_web and the crunk rule catalog pack rows are not wired.
