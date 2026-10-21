+++
id = "01M5FSSDC7EG5QA70CRABC8SMA"
title = "Read [rules.<id>] severity overrides and raise TIME001/TIME002 to Error in grimble.toml"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M44R5D47XBH3E2N3B8FNMT9F"
reporter = "lognd"
created = "2026-10-21T17:57:48Z"
updated = "2026-10-21T20:15:21Z"
scope = ["crates/grimble-check/src/**", "grimble.toml", "docs/design/rules.md"]
+++

Found while working ~8KVQQN5: rules.md 3.2 says this repository raises TIME001 and TIME002 to Error in its own config, but gob_rules::RuleSettings (the [rules.<id>] severity override) has no reader in any product, so the raise cannot be expressed yet. A scan of this repo's Rust and Python files finds no TIME001/TIME002 site, so the raise is safe once the override is read. Wire the override into the grimble check pipeline, add [rules.TIME001] and [rules.TIME002] severity = "error" to grimble.toml, and drop the waiting note from rules.md 3.2.
