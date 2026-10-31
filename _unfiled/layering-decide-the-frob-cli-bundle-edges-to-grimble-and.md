+++
id = "01M6949243QA9QCK0MN5ZZ33Y0"
title = "Layering: decide the frob-cli bundle edges to grimble and crunk-check"
type = "task"
category = "todo"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-31T14:02:07Z"
updated = "2026-10-31T14:02:07Z"
scope = ["crates/gob-dev/tests/layering.rs", "docs/design/boundaries.md"]

[[acceptance]]
text = "The frob-cli -> grimble and frob-cli -> crunk-check bundle edges are either removed from the layering allow-list by a boundary-respecting design or documented as permitted in boundaries.md and the test"
bound = false
+++

found while working ~DWMMH0A: the optional bundle feature edges are listed in the layering allow-list against this ticket.
