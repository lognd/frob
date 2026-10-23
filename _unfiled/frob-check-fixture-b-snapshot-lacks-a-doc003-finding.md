+++
id = "01M5NFNVB515TW2DH23FSH0MZS"
title = "frob-check fixture_b snapshot lacks a DOC003 finding"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-23T22:56:32Z"
updated = "2026-10-23T23:26:33Z"
scope = ["crates/frob-check/tests/**"]

[[acceptance]]
text = "Given the frob-check fixture_b snapshot, when equivalence::fixture_b_matches_the_recorded_findings runs, then it passes with the DOC003 finding recorded"
bound = true
+++
