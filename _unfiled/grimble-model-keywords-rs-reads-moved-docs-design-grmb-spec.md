+++
id = "01M6D2TV4TP485HAF6PXYK1JC2"
title = "grimble-model: keywords.rs reads moved docs/design/grmb-spec.md (3 tests fail)"
type = "bug"
category = "in-progress"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-11-02T02:53:50Z"
updated = "2026-11-11T02:41:37Z"
scope = ["crates/grimble-model/tests/keywords.rs", "changelog.d/**"]

[[acceptance]]
text = "Given the moved grmb-spec path, when grimble-model keywords tests run, then they read the new location and pass"
bound = false
+++
