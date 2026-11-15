+++
id = "01M7EXTZJS9H7Y784ARRG9GJ8B"
title = "grimble: make CONF 18.2 an insta snapshot test of check --text"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:20:42Z"
updated = "2026-11-15T06:20:42Z"
labels = ["no-story"]

[[acceptance]]
text = "A snapshot test runs check --text on the CONF 18.2 model and fails on drift"
bound = false
+++

Audit: /home/logan/projects/frob-audit2-grimble.md M1 (part 3). Remedy: conformance.md lines 26-85 become a snapshot test so docs cannot drift. Files: docs/design/grimble/conformance.md, crates/grimble/tests. Blocked by the two M1 fix tickets in spirit.
