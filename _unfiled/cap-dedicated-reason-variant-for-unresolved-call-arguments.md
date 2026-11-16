+++
id = "01M61Y35M4HHEFVJRMV8HFMF8H"
title = "CAP: dedicated Reason variant for unresolved call arguments"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-28T18:59:21Z"
updated = "2026-11-16T01:07:57Z"
labels = ["no-story"]
scope = ["crates/grimble-bind/src/caps.rs", "crates/grimble-bind/src/types.rs", "crates/grimble-bind/tests/it/caps.rs"]

[[acceptance]]
text = "unresolved arguments carry their own Reason, not UnresolvedEdge"
bound = false
+++

found while working ~5X9CAQE: unresolved arguments carry their own Reason, not UnresolvedEdge
