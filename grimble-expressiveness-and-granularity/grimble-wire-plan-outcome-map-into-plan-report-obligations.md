+++
id = "01M69BW9J521P25FVVAK6GAMTK"
title = "Grimble: wire plan_outcome_map into plan::report obligations"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-31T16:14:57Z"
updated = "2026-10-31T16:14:57Z"
idempotency_key = "wire-outcome-plan-0W79F8B"
scope = ["crates/grimble-bind/**", "crates/grimble-model/**"]

[[acceptance]]
text = "Given an impl whose boundary ErrorFacts are not Exact, when grimble check runs, then PLAN011 Unresolved is reported via plan_outcome_map and an outcome-map claim in the source resolves it to Conditional"
bound = false
+++

Follow-up of ~0W79F8B: plan_outcome_map in grimble-bind has no caller; nothing builds ErrorFacts per impl or parses outcome-map declarations. Sequence after ~03B2YRN (new grammar parser) if the declaration syntax changes.
