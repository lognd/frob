+++
id = "01M7EXV0GGRFVK94Z0XS720HNE"
title = "grimble-bind: rename emitted rung verified to covered; fix SPEC 17.1"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:20:43Z"
updated = "2026-11-15T06:20:43Z"
labels = ["no-story"]

[[acceptance]]
text = "Emitted status for unrun tests is covered, not verified"
bound = false

[[acceptance]]
text = "SPEC 17.1 and PLAN docs agree"
bound = false

[[acceptance]]
text = "frob graph consumer test passes with the new key"
bound = false
+++

Audit: ~/projects/frob-audit2-grimble.md M4. Evidence: tool emits verified where planning-semantics 12.8 says covered, for never-run tests; rollup key verified; SPEC 17.1 line 1893 inconsistent. Remedy: rename the rung to covered, fix SPEC 17.1; the grimble.graph/1 consumer in frob must follow. Crates: grimble-bind, grimble-verdict, frob graph consumer.
