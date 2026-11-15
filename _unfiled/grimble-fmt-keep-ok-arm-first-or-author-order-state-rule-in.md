+++
id = "01M7EXVJVC1J2PKK9233G1ARNS"
title = "grimble fmt: keep ok arm first (or author order); state rule in SPEC 9.6"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:21:02Z"
updated = "2026-11-15T06:21:02Z"
labels = ["no-story"]

[[acceptance]]
text = "fmt output keeps a documented arm order"
bound = false

[[acceptance]]
text = "fmt is idempotent in a test"
bound = false
+++

Audit: ~/projects/frob-audit2-grimble.md L2. fmt sorts arms alphabetically so the error arm precedes ok. Remedy: sort ok first or keep author order and document in SPEC 9.6. Crate: grimble-model printer.
