+++
id = "01M68WWE14NTX7QGN0T0W79F8B"
title = "Grimble: consume ErrorFacts resolution as opaque-cone Unresolved and accept outcome-map claims"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-31T11:52:53Z"
updated = "2026-10-31T16:14:55Z"
labels = ["no-story", "grimble"]
scope = ["crates/grimble-*/**"]

[[acceptance]]
text = "Given non-Exact ErrorFacts, when grimble plans an impl outcome map, then the gap is reported via the existing Unresolved path and an outcome-map declaration resolves it conditionally (assumed:<claim>)"
bound = true
+++

Follow-up of ~589WNWE: consumption side (ErrorFacts::resolution, with_outcome_map) exists in gob-ir only.
