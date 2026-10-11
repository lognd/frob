+++
id = "01M4M99GMQDG93W4X05A4HFP5X"
title = "Run GRL examples through the executor: build the example model and feed the example judge"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 5
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-11T01:30:00Z"
updated = "2026-10-11T16:14:27Z"
scope = ["crates/gob-plan/src/examples/**", "crates/gob-plan/tests/**", "crates/gob-plan/Cargo.toml", "Cargo.lock"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7EKNE5Q0NB0DKCH77AZX"

[[links]]
kind = "blocked-by"
target = "01M4MC43CFCTQ7TQCHCF0C0YRR"

[[acceptance]]
text = "Given a rule and a fire example whose source has one violation on line 3, when the runner executes it, then it passes and a clean variant fails with GRL016"
bound = true
+++

Follow-up of ~VB2EYG6, which landed the pure judge (markers, verdicts, GRL016 diff). This ticket lowers the rule (~CH77AZX), builds the example's gob-ir model from its source and sub-blocks, runs exec::outcome::outcomes, maps findings to Actual lines and calls judge.
