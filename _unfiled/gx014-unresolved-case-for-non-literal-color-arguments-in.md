+++
id = "01M5HW48CZPQ5KW8E70F63DZXF"
title = "GX014: unresolved case for non-literal Color arguments in prefab generators"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-22T13:17:08Z"
updated = "2026-10-22T16:45:47Z"
scope = ["crates/crunk-check/**"]

[[acceptance]]
text = "Given a prefab generator passing a non-literal Color argument, when GX014 runs, then the case is Unresolved and not clean or fired"
bound = false
+++

found while working ~Q1ABGXK: GX014 has fire and clean corpus cases but no unresolved case (P+). Decide what an undecidable Color argument reports, then drop the coverage-allowlist gap.
