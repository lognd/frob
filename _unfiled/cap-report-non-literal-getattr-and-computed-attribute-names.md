+++
id = "01M61QA7GY8CG9YQVFXQ71TFKF"
title = "CAP: report non-literal getattr and computed attribute names as Unresolved uses"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-28T17:00:53Z"
updated = "2026-11-15T23:29:35Z"
labels = ["no-story"]
scope = ["crates/gob-symbols/src/canon.rs"]

[[acceptance]]
text = "A non-literal getattr name is reported as a computed (Unresolved) use of its known prefix"
bound = false
+++

Found while working D36SRKP; documented limit of import resolution.
