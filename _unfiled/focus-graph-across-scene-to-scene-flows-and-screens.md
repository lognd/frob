+++
id = "01M5HA924E3PTBVH6J8EBXP7XW"
title = "Focus graph across scene-to-scene flows and screens"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T08:05:12Z"
updated = "2026-11-16T04:32:10Z"
labels = ["no-story"]
scope = ["crates/crunk-layout/**,crates/crunk-rules/**", "docs/reference/rules/GX00*.md", "crates/crunk-layout/src/focus_flow.rs", "crates/crunk-layout/src/lib.rs", "crates/crunk-layout/tests/it/focus.rs", "crates/crunk-rules/src/flow_files.rs", "crates/crunk-rules/src/host.rs", "crates/crunk-rules/src/lib.rs", "crates/crunk-rules/src/rules/gx002.md", "crates/crunk-rules/src/rules/gx002.rs", "crates/crunk-rules/src/rules/gx003.md", "crates/crunk-rules/src/rules/gx003.rs", "crates/crunk-rules/src/scene_docs.rs"]

[[acceptance]]
text = "GX002 and GX003 see across scenes: scenes joined by flow transitions are judged for scene-level reachability and stranding"
bound = true
+++

found while working Q2ZC9QM: the flows half of the focus graph is not built; GX002-GX005 see one scene at a time.

no-story: internal engineering task in crunk-layout; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
