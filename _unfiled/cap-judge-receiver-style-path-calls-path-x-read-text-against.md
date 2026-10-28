+++
id = "01M61Y35309KEQP2SPTQHP1AT8"
title = "CAP: judge receiver-style path calls (Path(x).read_text) against may args"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-28T18:59:21Z"
updated = "2026-10-28T18:59:21Z"
scope = ["crates/grimble-bind/src/caps.rs"]

[[acceptance]]
text = "receiver-style calls such as Path(x).read_text() are judged, not Unresolved, under an argument grant"
bound = false
+++

found while working ~5X9CAQE: receiver-style calls such as Path(x).read_text() are judged, not Unresolved, under an argument grant
