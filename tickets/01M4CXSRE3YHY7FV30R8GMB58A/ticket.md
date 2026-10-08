+++
id = "01M4CXSRE3YHY7FV30R8GMB58A"
title = "COH002 decision with effects (functional core, imperative shell), judged against grimble:shell and grimble:core roles"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4CXSN7VTEYX5AVSZVDX2WPZ"
reporter = "lognd"
created = "2026-10-08T04:54:28Z"
updated = "2026-10-08T04:54:28Z"
scope = ["changelog.d/**", "crates/grimble-check/**"]

[[acceptance]]
text = "Given a unit that branches on computed data and performs effects in the branches, when COH002 runs, then it fires unless the unit is a verified shell"
bound = false
+++

docs/design/cohesion.md 1.
