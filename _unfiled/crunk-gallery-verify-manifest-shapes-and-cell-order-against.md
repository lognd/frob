+++
id = "01M4YZCBRPDEDQY8KH6DWYQ5Z1"
title = "crunk-gallery: verify manifest shapes and cell order against the Python crunk gallery"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-15T05:08:26Z"
updated = "2026-11-09T02:49:37Z"
scope = ["crates/crunk-gallery/**"]

[[acceptance]]
text = "Golden tests pin the normalized manifest v1, v2 and v3 shapes"
bound = false

[[acceptance]]
text = "A golden file pins the cell enumeration order for the screens_v1_1 fixture"
bound = false

[[acceptance]]
text = "The crate README states that verification against the Python gallery was impossible"
bound = false
+++

Python crunk source was unavailable for ~AKETJJH; manifest v1-v3 shapes, cell enumeration order and GALLERY rule semantics were reconstructed from notes and fixtures. Diff crates/crunk-gallery against the Python list and fix any drift.
