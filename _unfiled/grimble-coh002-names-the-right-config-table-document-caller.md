+++
id = "01M7EXW686FY9TW3WKR56GWTD8"
title = "grimble: COH002 names the right config table; document caller-must-hold-callee-capability"
type = "task"
category = "todo"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-11-15T06:21:22Z"
updated = "2026-11-15T06:21:22Z"
labels = ["no-story"]

[[acceptance]]
text = "COH002 message names an existing config key"
bound = false

[[acceptance]]
text = "The guide explains the capability rule and goal evidence"
bound = false
+++

Audit: /home/logan/projects/frob-audit2-grimble.md friction log. COH002 asks the user to edit an unknown [coh] table; the caller-must-hold rule is unexplained in the guide; goals needing their own verified_by is not obvious. Files: crates/grimble-check/src/coh002.rs, docs/guides/grimble.md.
