+++
id = "01M4069W45P08YPC4YH4XZVMNC"
title = "frob board: text columns by category with WIP limits, expedite lane and card age"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:12:57Z"
updated = "2026-10-03T06:12:57Z"
idempotency_key = "m2-rel-board"
labels = ["milestone:2", "area:release", "release:0.532.0"]
scope = ["crates/frob-pm/src/board.rs", "crates/frob/src/board_cmd.rs"]

[[links]]
kind = "blocked-by"
target = "01M4069T76A6WSNHT3NZERXHAH"

[[links]]
kind = "blocked-by"
target = "01M4069VZVMHVZ15RSPZQRNCXY"

[[acceptance]]
text = "Given tickets in several categories, when frob board runs in text mode, then each column lists its cards with counts and limits"
bound = false

[[acceptance]]
text = "Given a ticket in progress for three days, when the board renders, then its age reads 3d"
bound = false
+++

Text mode only (JSON envelope carries the same columns): columns triage, todo, in-progress, blocked, done (recent); each header shows count and limit (red when exceeded); expedite lane first; each card shows handle, title, points, holder and age.
