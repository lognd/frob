+++
id = "01M7EXVM2KPYZPY7AACEJ315VZ"
title = "grimble fmt: preserve sorry because=/owner=/until= grammar (SPEC 11.1 debt_key)"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:21:03Z"
updated = "2026-11-15T06:21:03Z"
labels = ["no-story"]

[[acceptance]]
text = "fmt round-trips owner as ident"
bound = false

[[acceptance]]
text = "fmt idempotent on the sorry example"
bound = false
+++

Audit: /home/logan/projects/frob-audit2-grimble.md L9. fmt turns owner=logan into owner = "logan" though debt_key says owner = ident. Crate: grimble-model printer.
