+++
id = "01M6AJ93BY9CPG87769Z3ZVYCX"
title = "gob-ir def_use: avoid iterating all scope decls per unit (about 3.4s of cold coh pass)"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-01T03:26:03Z"
updated = "2026-11-01T05:25:33Z"
labels = ["creates:crates/gob-ir/src/defuse.rs"]
scope = ["crates/gob-ir/src/defuse.rs"]

[[acceptance]]
text = "A count-based test proves def_use work grows linearly with units"
bound = true
+++

gob_ir::def_use in crates/gob-ir/src/defuse.rs (~line 565) iterates all scope decls per unit; reported by the DEYY4PR implementer as ~3.4s of the baseline, unverified.
