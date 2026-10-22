+++
id = "01M5HYTAKXCZB6B2MAEM8X2G5Y"
title = "Bind api-extractor (TypeScript) to VERSION001"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T14:04:09Z"
updated = "2026-10-22T16:51:56Z"
scope = ["crates/gob-check/**", "changelog.d/**", "docs/**"]

[[acceptance]]
text = "Given api-extractor output whose API report differs from the committed report, when VERSION001 runs, then the diff maps to a VERSION001 Error on the committed report"
bound = true

[[acceptance]]
text = "Given api-extractor is not installed, when VERSION001 runs, then the tool is reported as unresolved (TOOL001)"
bound = true

[[acceptance]]
text = "Given clean, empty or malformed api-extractor output, when VERSION001 runs, then no finding is produced"
bound = false
+++

found while working BVDP7MK
