+++
id = "01M6AW0G2F3JHWZ2YFA4Y7KVMW"
title = "grimble check/graph warm median over profile budget (6.5s vs 5.8s)"
type = "task"
category = "in-progress"
priority = "high"
points = 5
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-01T06:16:06Z"
updated = "2026-11-01T06:41:02Z"
labels = ["creates:crates/grimble-check/**"]
scope = ["crates/grimble-check/**"]

[[acceptance]]
text = "profile job passes: grimble check and grimble graph warm medians at or under 5800 ms"
bound = true
+++

Run 41278673977 profile: grimble check warm 6572 ms, grimble graph warm 6487 ms vs budget 5800 ms. Profile the warm path (redundant per-stage re-folds since only FileSymbols is cached; row_hits and selector-fallback select still O(file); CodeFile::units recomputes unit_kind per call) and cut ~700 ms.
