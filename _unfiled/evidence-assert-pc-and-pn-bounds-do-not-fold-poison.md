+++
id = "01M4P3HCGW50BCT6YD0T7M99CH"
title = "evidence: assert Pc and Pn bounds do not fold poison (strengthen 3RECX85 coverage)"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-11T18:27:55Z"
updated = "2026-10-24T02:59:37Z"
scope = ["crates/frob-tests/**"]

[[acceptance]]
text = "a test fails if Pc/Pn bound evaluation folds a poison value into a passing result"
bound = true
+++
