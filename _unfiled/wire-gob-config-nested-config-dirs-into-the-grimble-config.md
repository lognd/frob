+++
id = "01M5A56QJM8VNX08Q2XJHK8825"
title = "Wire gob-config nested_config_dirs into the grimble config loader"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-19T13:21:52Z"
updated = "2026-11-02T14:11:47Z"
scope = ["crates/grimble-check/src/config.rs", "crates/grimble-check/src/product.rs"]

[[acceptance]]
text = "A nested grimble.toml loads as its own root only when listed in root [workspace] members"
bound = false
+++
