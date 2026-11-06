+++
id = "01M4P0SXFYYD9TE4F53NQ5SB96"
title = "dup T1: structural (AST-shape) clone check on frob land, scoped to changed symbols"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 5
parent = "01M4P0SQC82NJ7DV5BC3CAR5Y4"
reporter = "lognd"
created = "2026-10-11T17:40:09Z"
updated = "2026-11-06T06:46:38Z"
labels = ["no-story"]
scope = ["crates/grimble-arch/**", "crates/grimble-check/**", "crates/grimble/src/explain_cmd.rs", "crates/grimble-bind/src/lib.rs", "docs/design/dup.md", "docs/README.md", "docs/reference/rules/DUP004.md", "docs/reference/rules/README.md"]

[[acceptance]]
text = "Renamed-and-reordered clone of an existing function is detected on land"
bound = true

[[acceptance]]
text = "Result cached by input hash; retry costs under 100 ms"
bound = true

[[acceptance]]
text = "Works for every language gob-symbols supports"
bound = true
+++

dup T1: structural (renamed and reordered) clone detection scoped to changed files, as rule DUP004. no-story: one slice of the dup epic, no story of its own.
