+++
id = "01M4CXV46WX4E0WSVYJPYM7TRG"
title = "Fidelity measured, not declared: derive the level from capability cells and measure it with oracle corpora"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4CXTT0JWKFTX1HBB703QA80"
reporter = "lognd"
created = "2026-10-08T04:55:13Z"
updated = "2026-10-08T04:55:13Z"
scope = ["changelog.d/**", "crates/gob-caps/**", "crates/gob-symbols/**"]

[[acceptance]]
text = "Given an adapter declaring F2, when its corpus runs, then the measured cells justify the level or the build fails"
bound = false
+++

notes/review/formal-review-2026-10-08.md section 4 item 9; pairs with the incompleteness metric ticket (D119).
