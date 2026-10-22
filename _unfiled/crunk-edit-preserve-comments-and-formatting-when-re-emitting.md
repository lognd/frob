+++
id = "01M5H8MMRPN3RFSMP5KCEXPWC7"
title = "crunk edit: preserve comments and formatting when re-emitting TOML"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-22T07:36:34Z"
updated = "2026-10-22T17:57:41Z"
scope = ["crates/crunk/**", "docs/crunk/**"]

[[acceptance]]
text = "Given a crunk TOML file with comments and custom formatting, when crunk edit changes one key, then every comment and untouched line is byte-identical"
bound = true

[[acceptance]]
text = "Given an edit that adds a new key or table, then it is inserted without disturbing neighbouring comments, and a malformed file is an error that leaves it unchanged"
bound = false
+++

Cut from AFVVZ8Y: edit re-emits from a parsed tree, losing comments; move to toml_edit DocumentMut surgery.
