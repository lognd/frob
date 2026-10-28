+++
id = "01M61Y35M4HHEFVJRMV8HFMF8H"
title = "CAP: dedicated Reason variant for unresolved call arguments"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-28T18:59:21Z"
updated = "2026-10-28T18:59:21Z"
scope = ["crates/grimble-bind/src/caps.rs"]

[[acceptance]]
text = "unresolved arguments carry their own Reason, not UnresolvedEdge"
bound = false
+++

found while working ~5X9CAQE: unresolved arguments carry their own Reason, not UnresolvedEdge
