+++
id = "01M5B28YM1QJJ5PCZ7SJ5VX9W8"
title = "opt-in for xfail/skip/xpass to satisfy pytest evidence, counted as a distinct state"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-19T21:49:53Z"
updated = "2026-10-19T22:53:42Z"
scope = ["crates/frob-evidence/**", "crates/frob-tests/**"]
+++

follow-up of ~QMPSRAV: default exclusion and separate Capture.non_passing counts landed; no config opt-in exists yet to let non-passing outcomes satisfy evidence, nor are non_passing counts surfaced in the evidence record or frob test output. Also vitest/jest skipped are still only dropped, not counted.
