+++
id = "01M5B28YM1QJJ5PCZ7SJ5VX9W8"
title = "opt-in for xfail/skip/xpass to satisfy pytest evidence, counted as a distinct state"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-19T21:49:53Z"
updated = "2026-10-19T23:15:44Z"
scope = ["crates/frob-evidence/**", "crates/frob-tests/**", "crates/gob-dev/src/import_v1.rs", "docs/reference/config.md", "docs/schemas/config.json", "docs/design/build-test-ci.md"]

[[acceptance]]
text = "Pytest skipped/xfailed/xpassed satisfy evidence only via [tests] non_passing_counts, and counts are surfaced apart"
bound = true
+++

follow-up of ~QMPSRAV: default exclusion and separate Capture.non_passing counts landed; no config opt-in exists yet to let non-passing outcomes satisfy evidence, nor are non_passing counts surfaced in the evidence record or frob test output. Also vitest/jest skipped are still only dropped, not counted.
