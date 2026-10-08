+++
id = "01M4E0BWJNPXY0CG8ZK8HM4YHB"
title = "soundness proptest: model within N as a budget (truncation is Unknown), not as a path of at most N steps"
type = "task"
category = "todo"
priority = "medium"
points = 1
parent = "01M4CXTT0JWKFTX1HBB703QA80"
reporter = "lognd"
created = "2026-10-08T14:58:34Z"
updated = "2026-10-08T14:58:34Z"
scope = ["changelog.d/**", "crates/gob-ir/tests/**"]

[[acceptance]]
text = "Given a structure where the shortest path exceeds the budget, when evaluated, then the reference model and the evaluator both yield Unknown"
bound = false
+++

Coordinator decision 2026-10-08 (grl-spec 7.0.3): within N is a budget.
