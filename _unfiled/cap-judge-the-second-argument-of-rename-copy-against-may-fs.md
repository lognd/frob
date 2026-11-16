+++
id = "01M61Y356JN6KCHRD81WWJ56CZ"
title = "CAP: judge the second argument of rename/copy against may fs.write args"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-28T18:59:21Z"
updated = "2026-11-16T01:01:28Z"
labels = ["no-story"]
scope = ["crates/grimble-bind/src/caps.rs", "crates/grimble-bind/tests/it/caps.rs"]

[[acceptance]]
text = "the destination argument of rename/copy is judged too"
bound = true
+++

found while working ~5X9CAQE: the destination argument of rename/copy is judged too
