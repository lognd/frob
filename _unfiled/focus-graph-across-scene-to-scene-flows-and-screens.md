+++
id = "01M5HA924E3PTBVH6J8EBXP7XW"
title = "Focus graph across scene-to-scene flows and screens"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T08:05:12Z"
updated = "2026-11-16T04:24:05Z"
labels = ["no-story"]
scope = ["crates/crunk-layout/**,crates/crunk-rules/**", "docs/reference/rules/GX00*.md"]

[[acceptance]]
text = "GX002 and GX003 see across scenes: scenes joined by flow transitions are judged for scene-level reachability and stranding"
bound = false
+++

found while working Q2ZC9QM: the flows half of the focus graph is not built; GX002-GX005 see one scene at a time.

no-story: internal engineering task in crunk-layout; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
