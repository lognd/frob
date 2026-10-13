+++
id = "01M4CXSQB9YJGH0FRSHX5ECTEM"
title = "COH001 independent jobs: slice components with lo (May merged) and hi (Must only) bounds and extract-unit fix"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M4CXSN7VTEYX5AVSZVDX2WPZ"
reporter = "lognd"
created = "2026-10-08T04:54:27Z"
updated = "2026-10-13T14:17:51Z"
scope = ["changelog.d/**", "crates/grimble-check/**", "crates/gob-check/**"]

[[acceptance]]
text = "Given fire, clean and Unresolved fixtures per language, when COH001 runs, then it fires only when lo >= 2, is clean when hi <= 1, and names the May witnesses otherwise"
bound = true
+++

docs/design/cohesion.md 1.1. Owner grimble.
