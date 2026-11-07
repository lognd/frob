+++
id = "01M6SNTWBS6DV2VMAPQASQ6BMN"
title = "grimble-lints: migrate err family to the universal model"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M6SJHBH2JK72HAE60AFYDFWX"
reporter = "lognd"
created = "2026-11-07T00:16:47Z"
updated = "2026-11-07T00:16:47Z"
scope = ["crates/grimble-lints/src/**"]

[[acceptance]]
text = "ERR001-003 classified in docs/design/grimble/lint-classification.md is migrated to U queries where U provides them, behaviour identical on existing tests, and a test runs it on every adapter language"
bound = false
+++

Child of ~AFYDFWX. See docs/design/grimble/lint-classification.md. Report missing U queries rather than inventing them.
