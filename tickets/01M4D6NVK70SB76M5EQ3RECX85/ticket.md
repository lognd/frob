+++
id = "01M4D6NVK70SB76M5EQ3RECX85"
title = "Property test for rule polarity mapping (Pc, P+, P-) against K3 verdicts once the GRL executor exists"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M4CXTT0JWKFTX1HBB703QA80"
reporter = "lognd"
created = "2026-10-08T07:29:37Z"
updated = "2026-10-08T07:29:37Z"
scope = ["changelog.d/**", "crates/gob-plan/**", "crates/gob-ir/**"]

[[acceptance]]
text = "Given random rule programs and structures, when interpreted, then every finding and every certified clean holds in every sampled completion"
bound = false
+++

Follow-up from ~JVT37ES: the gob-ir layer is covered; RuleProgram interpret and taint are not.
