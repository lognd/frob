+++
id = "01M63G1NCSMT29PG74CWXW0P9A"
title = "Grimble LOG rules: advisory (Warn) severity for advisory atoms"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-29T09:32:21Z"
updated = "2026-11-06T22:45:03Z"
labels = ["no-story"]
scope = ["crates/grimble-check/src/log/**"]
+++

found while working ~JKKJPTT: advisory atoms are not reported because the pass only emits Error
