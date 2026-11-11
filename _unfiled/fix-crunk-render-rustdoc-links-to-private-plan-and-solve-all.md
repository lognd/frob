+++
id = "01M75JF1F1GKATFSDDPDF55K00"
title = "Fix crunk render rustdoc links to private Plan and solve_all"
type = "bug"
category = "in-progress"
priority = "high"
points = 1
reporter = "lognd"
created = "2026-11-11T15:08:47Z"
updated = "2026-11-11T15:09:08Z"
scope = ["crates/crunk/src/render.rs", "changelog.d/**"]

[[acceptance]]
text = "crunk render.rs module doc no longer intra-doc-links private Plan or solve_all, so the rustdoc docs step passes"
bound = true
+++
