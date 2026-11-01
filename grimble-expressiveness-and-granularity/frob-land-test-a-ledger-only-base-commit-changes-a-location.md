+++
id = "01M6C6NBSPEQC636AKEYZZ5J1Y"
title = "frob-land test a_ledger_only_base_commit_changes_a_location_less_pm_finding fails: low ready queue trips PM033"
type = "bug"
category = "in-progress"
priority = "high"
points = 2
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-01T18:41:30Z"
updated = "2026-11-01T18:51:32Z"
scope = ["crates/frob-land/tests/land.rs", "crates/frob-land/Cargo.toml", "Cargo.lock", "changelog.d/01M6C6NBSPEQC636AKEYZZ5J1Y.fixed.md"]

[[acceptance]]
text = "Given the fixture, when the test runs in CI, then it passes without a PM033 low-ready-queue finding"
bound = true
+++
