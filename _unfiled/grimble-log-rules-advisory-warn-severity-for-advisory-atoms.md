+++
id = "01M63G1NCSMT29PG74CWXW0P9A"
title = "Grimble LOG rules: advisory (Warn) severity for advisory atoms"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-29T09:32:21Z"
updated = "2026-11-11T01:31:34Z"
labels = ["no-story"]
scope = ["crates/grimble-check/src/log/**", "changelog.d/**"]
+++

found while working ~JKKJPTT: advisory atoms are not reported because the pass only emits Error
