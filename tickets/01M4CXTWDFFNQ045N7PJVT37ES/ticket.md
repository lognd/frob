+++
id = "01M4CXTWDFFNQ045N7PJVT37ES"
title = "Property tests that falsify Theorems 2 and 3 over random terms, scope graphs and completions of May and Unknown edges"
type = "task"
category = "in-progress"
priority = "high"
points = 5
parent = "01M4CXTT0JWKFTX1HBB703QA80"
reporter = "lognd"
created = "2026-10-08T04:55:05Z"
updated = "2026-10-08T06:45:10Z"
scope = ["changelog.d/**", "crates/gob-ir/**"]

[[acceptance]]
text = "Given proptest over random structures, completions and formulas (atoms, not/and/or, some/no, count, bounded and unbounded reach), when run, then every definite answer equals the classical answer in every sampled completion, and closed structures never yield Unknown"
bound = true
+++

notes/review/formal-review-2026-10-08.md section 4 item 8. Would have found H1, the polarity bug and the within bug.
