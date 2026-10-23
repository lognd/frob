+++
id = "01M5HJ07DTC2JQT9MP5T0TGDAS"
title = "COH002: effects capability from language adapters"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-22T10:20:11Z"
updated = "2026-10-23T08:57:19Z"
scope = ["crates/grimble-check/**", "docs/design/**", "docs/reference/rules/**", "Cargo.lock", "docs/reference/config.md", "docs/schemas/**"]

[[acceptance]]
text = "COH002 decides effects from a language-adapter capability rather than the callee-name vocabulary"
bound = true

[[acceptance]]
text = "COH002 fire and no-fire tests exist for at least two adapter languages, and unresolved when an adapter lacks the capability"
bound = true
+++

Replace the callee-name vocabulary with a real effects capability from the adapters.
