+++
id = "01M6C6NBJSSAVBR59RBMPWW9VP"
title = "evidence add must not leave .grimble state in the repo (design stamp spawns grimble graph)"
type = "bug"
category = "in-progress"
priority = "high"
points = 2
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-01T18:41:30Z"
updated = "2026-11-01T18:42:53Z"
scope = ["crates/frob-evidence/src/design.rs", "crates/grimble-check/src/lib.rs", "crates/grimble/src/graph_cmd.rs", "crates/grimble/src/lib.rs"]

[[acceptance]]
text = "Given a repo with no grimble sources, when evidence add runs, then no .grimble files are created and the e2e init loop and quickstart tests pass"
bound = false
+++
