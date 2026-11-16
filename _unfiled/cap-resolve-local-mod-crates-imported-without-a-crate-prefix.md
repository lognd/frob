+++
id = "01M61QA7KBV7444W3YFT432YR1"
title = "CAP: resolve local mod crates imported without a crate:: prefix"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-28T17:00:53Z"
updated = "2026-11-16T00:17:01Z"
labels = ["no-story"]
scope = ["crates/gob-symbols/src/canon.rs"]

[[acceptance]]
text = "A Rust use of a sibling local mod crate without a crate:: prefix resolves to that crate, covered by a test in canon.rs"
bound = true
+++

Found while working D36SRKP; documented limit of import resolution.
