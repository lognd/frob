+++
id = "01M61Y356JN6KCHRD81WWJ56CZ"
title = "CAP: judge the second argument of rename/copy against may fs.write args"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-28T18:59:21Z"
updated = "2026-10-28T18:59:21Z"
scope = ["crates/grimble-bind/src/caps.rs"]

[[acceptance]]
text = "the destination argument of rename/copy is judged too"
bound = false
+++

found while working ~5X9CAQE: the destination argument of rename/copy is judged too
