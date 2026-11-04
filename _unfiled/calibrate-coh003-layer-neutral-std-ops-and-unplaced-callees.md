+++
id = "01M6H3ZX3SKEK9D4PTC4VEFR2D"
title = "Calibrate COH003: layer-neutral std ops and unplaced callees, then burn down residue"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-03T16:31:02Z"
updated = "2026-11-04T02:28:10Z"
labels = ["no-story"]
scope = ["crates/grimble-lints/**", "crates/gob-check/**", "frob.toml", "crates/grimble-check/**", "docs/**", "crates/gob-plan/src/grl/parse/cond.rs"]

[[acceptance]]
text = "COH003 rule treats std operators and string/slice methods as layer-neutral"
bound = true

[[acceptance]]
text = "frob.toml has no rules.COH003 table and frob check reports zero COH003 findings"
bound = true
+++

Measured under ~MTBE4QF: with COH003 on, 4228 findings (2632 errors, 1596 unresolved). 1919 are [] index/slice, ~690 std string/slice methods (find, trim, read, rsplit, strip). Make built-in operators and std string/slice methods layer-neutral; make unplaced callees non-failing or declare attr layer/owns in the grimble model; re-measure; fix the ~20 residue; delete [rules.COH003] off table.
