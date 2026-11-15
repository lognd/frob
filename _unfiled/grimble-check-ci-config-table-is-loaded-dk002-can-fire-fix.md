+++
id = "01M7EXW4PYJBEFCRK06K9MYF4Z"
title = "grimble-check: [ci] config table is loaded; DK002 can fire; fix max_timeout doc"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:21:20Z"
updated = "2026-11-15T06:21:20Z"
labels = ["no-story"]

[[acceptance]]
text = "A [ci] table in grimble.toml changes CiConfig"
bound = false

[[acceptance]]
text = "DK002 fires in a fixture"
bound = false

[[acceptance]]
text = "Config reference and architecture.md state the code default"
bound = false
+++

Audit: ~/projects/frob-audit-grimble-crunk.md M5. crates/grimble-check/src/product.rs:481 uses CiConfig::default(); related crates/grimble-ci/src/lib.rs:99-122; docs DK002.md, CI005.md, DK004.md. max_timeout default 30 in docs/design/shared/architecture.md:327-328 but 60 in code. Remedy: load a [ci] ConfigTable, add to config reference, fix architecture.md.
