+++
id = "01M6SNTWXQ02EDA6ZB70W3WZW0"
title = "grimble-lints: migrate unity family to the universal model"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M6SJHBH2JK72HAE60AFYDFWX"
reporter = "lognd"
created = "2026-11-07T00:16:48Z"
updated = "2026-11-07T00:16:48Z"
scope = ["crates/grimble-lints/src/**"]

[[acceptance]]
text = "UNITY201/202/301/302 and the Unity PAIR001 vocabulary classified in docs/design/grimble/lint-classification.md is migrated to U queries where U provides them, behaviour identical on existing tests, and a test runs it on every adapter language"
bound = false
+++

Child of ~AFYDFWX. See docs/design/grimble/lint-classification.md. Report missing U queries rather than inventing them.
