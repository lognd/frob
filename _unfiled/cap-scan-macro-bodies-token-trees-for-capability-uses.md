+++
id = "01M61QA7EFH66FJT0092G5R8FT"
title = "CAP: scan macro bodies (token trees) for capability uses"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-28T17:00:53Z"
updated = "2026-11-15T23:17:02Z"
labels = ["no-story"]
scope = ["crates/gob-symbols/src/canon.rs"]

[[acceptance]]
text = "Calls spelled inside macro invocation argument token trees are extracted as path uses"
bound = false
+++

Found while working D36SRKP; documented limit of import resolution.
