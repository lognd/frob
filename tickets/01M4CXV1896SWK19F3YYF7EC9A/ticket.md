+++
id = "01M4CXV1896SWK19F3YYF7EC9A"
title = "One relational structure for rules: lower SymbolGraph status edges into U relations with lo/hi"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M4CXTT0JWKFTX1HBB703QA80"
reporter = "lognd"
created = "2026-10-08T04:55:10Z"
updated = "2026-10-08T04:55:10Z"
scope = ["changelog.d/**", "crates/gob-ir/**", "crates/gob-symbols/**"]

[[acceptance]]
text = "Given a rule reading call or import edges, when evaluated, then it reads one relation with status from gob-ir, and SymbolGraph is a view over it"
bound = false
+++

notes/review/formal-review-2026-10-08.md section 4 item 4.
