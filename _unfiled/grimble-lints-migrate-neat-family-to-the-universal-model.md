+++
id = "01M6SNTWTRT3CWHE94KKM8C4P3"
title = "grimble-lints: migrate neat family to the universal model"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-07T00:16:48Z"
updated = "2026-11-07T02:47:43Z"
scope = ["crates/grimble-lints/src/**", "docs/design/grimble/lint-classification.md"]

[[acceptance]]
text = "NEAT010/NEAT031 classified in docs/design/grimble/lint-classification.md is migrated to U queries where U provides them, behaviour identical on existing tests, and a test runs it on every adapter language"
bound = true
+++

Child of ~AFYDFWX. See docs/design/grimble/lint-classification.md. Report missing U queries rather than inventing them.
