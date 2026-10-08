+++
id = "01M4CXV36WX1C2T64J454ECDV7"
title = "Applicability resolver reads the matrix for parsed files; GRL needs become capabilities, side relations move to reads"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4CXTT0JWKFTX1HBB703QA80"
reporter = "lognd"
created = "2026-10-08T04:55:12Z"
updated = "2026-10-08T04:55:12Z"
scope = ["changelog.d/**", "crates/gob-check/**", "crates/gob-plan/**"]

[[acceptance]]
text = "Given a GRL rule needing a capability a language lacks, when checked on that language, then the subject is NotApplicable statically, never a fourth runtime value"
bound = false
+++

notes/review/formal-review-2026-10-08.md section 4 item 7 (applicability.rs 155-180, grl/parse/rule.rs 302).
