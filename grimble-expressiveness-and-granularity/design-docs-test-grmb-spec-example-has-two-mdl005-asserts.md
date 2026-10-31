+++
id = "01M69SKDAD3QG4NVVS6GQBE1CG"
title = "design_docs test grmb_spec_example_has_two_mdl005 asserts spec text the cycle rewrites removed"
type = "bug"
category = "in-progress"
priority = "high"
points = 1
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-31T20:14:46Z"
updated = "2026-10-31T20:33:41Z"
idempotency_key = "design-docs-mdl005-stale"
scope = ["crates/grimble-check/tests/design_docs.rs"]

[[acceptance]]
text = "design_docs passes on experimental: the test asserts the MDL005 selector-example text that grmb-spec.md now carries, or is rebound to the section that does"
bound = true
+++

CI run 41236432024 (ubuntu) failed only this test at design_docs.rs:39: grmb-spec.md no longer contains "two MDL005 Warn findings". Fix the assertion to track the current spec wording (or drop it if the example was intentionally removed). Sequence after DJEDY70 (scope overlap on crates/grimble-check).
