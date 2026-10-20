+++
id = "01M4M8EJA0RAXE090V8X84157K"
title = "Record fixed and dismissed findings across runs for the precision ledger"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-11T01:15:17Z"
updated = "2026-10-11T01:15:17Z"
scope = ["crates/gob-rules/**", "crates/gob-check/**"]
+++

found while working ~B2ZBRER: PrecisionLedger has add_fixed and add_dismissed but nothing records them between runs; fixed counts need history and dismissals need a verb with a reason
