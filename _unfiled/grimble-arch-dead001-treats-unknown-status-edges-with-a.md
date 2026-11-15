+++
id = "01M7EXW5KPAM43SNE80SEY4N5D"
title = "grimble-arch: DEAD001 treats Unknown-status edges with a target as May"
type = "task"
category = "todo"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-11-15T06:21:21Z"
updated = "2026-11-15T06:21:21Z"
labels = ["no-story"]

[[acceptance]]
text = "A fixture with an Unknown edge to a target yields Unresolved, not dead"
bound = false
+++

Audit: ~/projects/frob-audit-grimble-crunk.md L11. crates/grimble-arch/src/dead.rs:156 'Status::Unknown => {}'. Remedy: treat as May (Unresolved, EdgeUnknown).
