+++
id = "01M6SNTWMPXFSGPZNKVH0R1VGM"
title = "grimble-lints: migrate time family to the universal model"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-07T00:16:48Z"
updated = "2026-11-07T02:08:26Z"
scope = ["crates/grimble-lints/src/**"]

[[acceptance]]
text = "TIME001-002 classified in docs/design/grimble/lint-classification.md is migrated to U queries where U provides them, behaviour identical on existing tests, and a test runs it on every adapter language"
bound = false
+++

Child of ~AFYDFWX. See docs/design/grimble/lint-classification.md. Report missing U queries rather than inventing them.
