+++
id = "01M6SNTWETXZ46BBKCFSEME5JK"
title = "grimble-lints: migrate res family to the universal model"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-07T00:16:48Z"
updated = "2026-11-07T01:54:15Z"
scope = ["crates/grimble-lints/src/**", "docs/design/grimble/lint-classification.md"]

[[acceptance]]
text = "RES001 classified in docs/design/grimble/lint-classification.md is migrated to U queries where U provides them, behaviour identical on existing tests, and a test runs it on every adapter language"
bound = true
+++

Child of ~AFYDFWX. See docs/design/grimble/lint-classification.md. Report missing U queries rather than inventing them.
