+++
id = "01M4CTE9W9QH6SBZSJ3E0E8M28"
title = "Tests: consolidate integration-test binaries per crate and run frob CLI tests in process by default (audit M17)"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-08T03:55:47Z"
updated = "2026-10-08T03:55:47Z"
scope = ["changelog.d/**", "crates/*/tests/**", "crates/*/Cargo.toml", "crates/gob-testsupport/**"]

[[acceptance]]
text = "Given the ci nextest profile, when the suite runs on quasar, then wall time drops by at least 25 percent against the recorded baseline with no test removed"
bound = false
+++

notes/review/audit-2026-10-07.md M17. Suite CPU is dominated by tests spawning the debug binary (build-test-ci.md section 5).
