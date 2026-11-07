+++
id = "01M6SNTWHRVDJ0ZEW5MMP46BP8"
title = "grimble-lints: migrate path family to the universal model"
type = "task"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-07T00:16:48Z"
updated = "2026-11-07T00:26:13Z"
scope = ["crates/grimble-lints/src/**"]

[[acceptance]]
text = "PATH001-003 classified in docs/design/grimble/lint-classification.md is migrated to U queries where U provides them, behaviour identical on existing tests, and a test runs it on every adapter language"
bound = false
+++

Child of ~AFYDFWX. See docs/design/grimble/lint-classification.md. Report missing U queries rather than inventing them.
