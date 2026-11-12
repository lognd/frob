+++
id = "01M5H15J1MN75F1TAA820Y2X8T"
title = "Validate component anatomy against solved scene subtrees"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T05:26:00Z"
updated = "2026-11-12T10:02:39Z"
labels = ["no-story"]
scope = ["crates/crunk-rules/**"]

[[acceptance]]
text = "Given a component spec with anatomy nodes and a solved scene subtree for that component, when the anatomy rule runs, then each anatomy node is checked against the subtree and a node absent from it is reported"
bound = false
+++

Cut from ~D6TTN3F: anatomy nodes are checked only against the spec list, not a scene subtree.

no-story: internal engineering task in crunk-rules; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
