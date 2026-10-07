+++
id = "01M48R029HFBJ3PKQX5GBBKJ6V"
title = "Pipeline runs RuleDefs: no hand group wiring, inapplicable reasons reported"
type = "story"
category = "in-progress"
priority = "high"
parent = "01M48QZYWAMKC7MXHQ6AYNV7BN"
reporter = "lognd"
created = "2026-10-06T13:56:06Z"
updated = "2026-10-07T15:39:58Z"
scope = ["crates/gob-check/**", "crates/gob-rules/**", "docs/design/rule-authoring.md"]

[[links]]
kind = "blocked-by"
target = "01M48R00MZS92F2KY5T60SBHYV"

[[links]]
kind = "blocked-by"
target = "01M48R01QSDTBKNPREQPBJ6GPZ"

[[acceptance]]
text = "a toy product with one file rule and one repo rule runs with no group wiring"
bound = false

[[acceptance]]
text = "inapplicable reasons are reported once in JSON and text"
bound = false

[[acceptance]]
text = "zero subjects for a must_measure rule is the required Unresolved"
bound = false
+++

M5: gob-check runs the product's RuleDef list (file, repo, stage bodies); delete hand-wired repo groups, file checks and product applicable/includes for rules; must_measure uses Measured. Design: docs/design/rule-authoring.md (D107); detail and the failure table: notes/research/rule-authoring.md section 4.
