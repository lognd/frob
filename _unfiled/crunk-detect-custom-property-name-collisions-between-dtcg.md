+++
id = "01M5GY2ZA5ER31SEFAW61ZPY4R"
title = "crunk: detect custom property name collisions between DTCG token paths"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T04:32:10Z"
updated = "2026-11-12T06:11:39Z"
labels = ["no-story"]
scope = ["crates/crunk-tokens/**", "changelog.d/01M5GY2ZA5ER31SEFAW61ZPY4R.*"]

[[acceptance]]
text = "Given two DTCG token paths that map to the same CSS custom property name, when tokens are loaded, then a collision error names both paths and the property"
bound = false
+++

found while working ~62C50FH

no-story: internal engineering task in crunk-tokens; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
