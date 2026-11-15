+++
id = "01M7EXXP1YXB5DY9WKF73E4B3S"
title = "grimble-bind: member-level contract diff judged by compat= (G01)"
type = "task"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-15T06:22:11Z"
updated = "2026-11-15T06:22:11Z"
labels = ["no-story"]

[[acceptance]]
text = "Removing a member under compat= raises an Error"
bound = false

[[acceptance]]
text = "Adding an optional member is clean"
bound = false

[[acceptance]]
text = "Unknown fidelity stays Unresolved"
bound = false
+++

Research: ~/projects/frob-research-lifecycle.md rec 1 (G01,G02), part 1 of 3. SYS006 detects digest inequality only. Add member-level diff of the Contract facet: removed, renamed, retyped or newly required member is an Error; added optional member is clean. Crates: grimble-bind, grimble-model. Note: the ticket list had no pre-filed lifecycle ticket for this.
