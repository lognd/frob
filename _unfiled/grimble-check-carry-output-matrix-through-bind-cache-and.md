+++
id = "01M6RSBRV13JSNWD55VA3YCEZ9"
title = "grimble-check: carry Output.matrix through bind_cache and show full capability matrix in check --summary"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-06T15:59:12Z"
updated = "2026-11-12T12:29:46Z"
scope = ["crates/grimble-check/src/**"]
+++

Found while working ~Z7G326G. grimble-bind now records Output.matrix (per-node cell counts, incl. Denied). summary.rs derives cells from CAP findings only and bind_cache.rs does not encode Output.matrix; consume and serialize it so --summary shows the full matrix.
