+++
id = "01M61QA7GY8CG9YQVFXQ71TFKF"
title = "CAP: report non-literal getattr and computed attribute names as Unresolved uses"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-28T17:00:53Z"
updated = "2026-11-15T23:36:22Z"
labels = ["no-story"]
scope = ["crates/gob-symbols/src/canon.rs"]

[[acceptance]]
text = "A non-literal getattr name is reported as a computed (Unresolved) use of its known prefix"
bound = true
+++

Found while working D36SRKP; documented limit of import resolution.
