+++
id = "01M61QA7BRC843EJ1QNAG8HHEC"
title = "CAP: follow glob imports in import-resolved capability uses"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-28T17:00:52Z"
updated = "2026-11-15T22:30:55Z"
labels = ["no-story"]
scope = ["crates/gob-symbols/src/canon.rs"]

[[acceptance]]
text = "A Rust name no scope binds while a glob import is in force is emitted with the glob modules in PathUse::wildcards"
bound = false
+++

Found while working D36SRKP; documented limit of import resolution.
