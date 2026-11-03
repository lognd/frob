+++
id = "01M6BZYETHGKPJDZF20JQ4J84G"
title = "Move CAP002 onto the capability matrix (public matrix API in grimble-bind)"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-01T16:44:08Z"
updated = "2026-11-03T05:20:13Z"
scope = ["crates/grimble-bind/src/caps.rs", "changelog.d/*JQ4J84G*"]

[[acceptance]]
text = "Given the grimble-bind matrix, when CAP002 evaluates, then it reads cells from a public matrix API shared with the grimble matrix verb, and the verb no longer reconstructs cells from CAP findings"
bound = false
+++
