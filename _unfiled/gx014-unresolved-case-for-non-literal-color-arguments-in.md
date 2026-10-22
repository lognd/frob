+++
id = "01M5HW48CZPQ5KW8E70F63DZXF"
title = "GX014: unresolved case for non-literal Color arguments in prefab generators"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-22T13:17:08Z"
updated = "2026-10-22T17:07:51Z"
scope = ["crates/crunk-check/**", "crates/gob-mdtest/coverage-allowlist.toml", "docs/reference/rules/GX014.md"]

[[acceptance]]
text = "Given a prefab generator building a Color or Color32 from arguments that are not all numeric literals (variable, field, method call or ternary), when GX014 runs, then the case is Unresolved, not clean and not fired"
bound = true

[[acceptance]]
text = "Given a prefab generator calling a Color method (Color.Lerp, Color.HSVToRGB) whose result cannot be judged, when GX014 runs, then the case is Unresolved, while Color.clear stays clean"
bound = true

[[acceptance]]
text = "Given a prefab generator passing named all-literal arguments to new Color, when GX014 runs, then the literal fires rather than going Unresolved"
bound = true
+++

found while working ~Q1ABGXK: GX014 has fire and clean corpus cases but no unresolved case (P+). Decide what an undecidable Color argument reports, then drop the coverage-allowlist gap.
