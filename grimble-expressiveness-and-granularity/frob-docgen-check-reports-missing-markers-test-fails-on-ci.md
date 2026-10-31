+++
id = "01M69P2ZNB0CYS4FGRV3PS6T67"
title = "frob-docgen check_reports_missing_markers test fails on CI ubuntu"
type = "bug"
category = "in-progress"
priority = "high"
points = 2
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-31T19:13:22Z"
updated = "2026-10-31T19:29:59Z"
idempotency_key = "ci-docgen-markers"
scope = ["crates/frob-docgen/**"]

[[acceptance]]
text = "check_reports_missing_markers_unknown_commands_and_orphans passes on CI ubuntu"
bound = true
+++

CI run 41230707415: generate.rs:267 assertion left (0, 58) right (0, 0); likely environment or cwd dependent.
