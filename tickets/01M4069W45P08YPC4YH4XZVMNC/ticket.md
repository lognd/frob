+++
id = "01M4069W45P08YPC4YH4XZVMNC"
title = "frob board: text columns by category with WIP limits, expedite lane and card age"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:12:57Z"
updated = "2026-10-03T16:55:04Z"
idempotency_key = "m2-rel-board"
labels = ["milestone:2", "area:release"]
scope = ["crates/frob-pm/src/board.rs", "crates/frob/src/board_cmd.rs", "crates/frob-pm/src/lib.rs", "crates/frob/Cargo.toml", "crates/frob/src/lib.rs", "crates/frob/tests/board.rs", "crates/frob/tests/snapshots/board__board_text_100.snap", "crates/frob/tests/snapshots/board__board_text_50_stacked.snap", "docs/reference/cli/frob.md", "docs/design/releases.md"]

[[links]]
kind = "blocked-by"
target = "01M4069T76A6WSNHT3NZERXHAH"

[[links]]
kind = "blocked-by"
target = "01M4069VZVMHVZ15RSPZQRNCXY"

[[acceptance]]
text = "Given tickets in several categories, when frob board runs in text mode, then each column lists its cards with counts and limits"
bound = true

[[acceptance]]
text = "Given a ticket in progress for three days, when the board renders, then its age reads 3d"
bound = true
+++

Text mode only (JSON envelope carries the same columns): columns triage, todo, in-progress, blocked, done (recent); each header shows count and limit (red when exceeded); expedite lane first; each card shows handle, title, points, holder and age.
