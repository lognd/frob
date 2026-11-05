+++
id = "01M6PB6EBDB090VT43A0T9K5D0"
title = "docs: note CAP001 severity layering in binding.md"
type = "docs"
category = "todo"
priority = "medium"
points = 1
parent = "01M4P0SQC82NJ7DV5BC3CAR5Y4"
reporter = "lognd"
created = "2026-11-05T17:13:09Z"
updated = "2026-11-05T17:13:09Z"
labels = ["no-story", "good-first"]
scope = ["docs/design/grimble/binding.md"]

[[acceptance]]
text = "Given binding.md, when a reader looks up CAP001, then it states severity comes from [packs.severity], then the atom row, then Error"
bound = false
+++

Document the CAP001 severity resolution order landed in K4EMP90.

## Start here

- Files to read first: docs/design/grimble/binding.md
- Test command: frob check --files docs/design/grimble/binding.md
- Who to ask: lognd
