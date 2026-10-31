+++
id = "01M4M8EJA0RAXE090V8X84157K"
title = "Record fixed and dismissed findings across runs for the precision ledger"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-11T01:15:17Z"
updated = "2026-10-31T09:02:41Z"
labels = ["no-story"]
scope = ["crates/gob-rules/**", "crates/gob-check/**"]

[[acceptance]]
text = "Fixed findings are recorded across runs (history-backed) and feed PrecisionLedger::add_fixed"
bound = true

[[acceptance]]
text = "A dismiss verb records a dismissal with a required reason and feeds PrecisionLedger::add_dismissed; both persist between runs"
bound = true
+++

found while working ~B2ZBRER: PrecisionLedger has add_fixed and add_dismissed but nothing records them between runs; fixed counts need history and dismissals need a verb with a reason

no-story: internal engineering task in gob-rules; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
